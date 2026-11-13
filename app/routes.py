import secrets
from datetime import date, datetime

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import and_, func, or_, select, update
from werkzeug.security import check_password_hash, generate_password_hash

from .models import PaymentType, Request, Status, User, WorkType, db, tickets_select
from .validators import LOGIN_RE, validate_registration, validate_ticket

bp = Blueprint("main", __name__)

PER_PAGE = 5

LOOKUP = {
    "work_types": WorkType,
    "payment_types": PaymentType,
    "statuses": Status,
}


def inject_template_context():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return {"csrf": session["csrf"], "me": current_user()}


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


@bp.before_request
def protect_post():
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        if not token or token != session.get("csrf"):
            abort(400)


@bp.get("/")
def home():
    return render_template("home.html")


@bp.get("/guide")
def guide():
    return render_template("guide.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return _home_for_role()
    errors = {}
    form = {
        "login": "",
        "full_name": "",
        "phone": "",
        "email": "",
    }
    if request.method == "POST":
        errors, cleaned = validate_registration(request.form)
        form = cleaned
        if not errors:
            taken = db.session.execute(
                select(User.id).where(User.login == cleaned["login"])
            ).scalar_one_or_none()
            if taken:
                errors["login"] = "Такой логин уже занят."
            else:
                db.session.add(User(
                    login=cleaned["login"],
                    password_hash=generate_password_hash(cleaned["password"], method="pbkdf2:sha256"),
                    full_name=cleaned["full_name"],
                    phone=cleaned["phone"],
                    email=cleaned["email"],
                    role="user",
                ))
                db.session.commit()
                flash("Аккаунт создан. Войдите, используя логин и пароль.", "success")
                return redirect(url_for("main.login"))
    return render_template("register.html", errors=errors, form=form), (400 if errors else 200)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return _home_for_role()
    error = None
    form_login = ""
    if request.method == "POST":
        form_login = " ".join(request.form.get("login", "").split()).lower()
        password = request.form.get("password", "")
        user = None
        if form_login:
            user = db.session.execute(
                select(User).where(User.login == form_login)
            ).scalar_one_or_none()
        if not user or not check_password_hash(user.password_hash, password):
            error = "Неверный логин или пароль."
        else:
            session.clear()
            session["user_id"] = user.id
            session["csrf"] = secrets.token_hex(16)
            return _home_for_role()
    status = 400 if error else 200
    return render_template("login.html", error=error, form_login=form_login), status


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.home"))


@bp.get("/api/login-available")
def login_available():
    login_value = " ".join(request.args.get("login", "").split()).lower()
    if not LOGIN_RE.match(login_value):
        return jsonify(available=False, reason="format")
    taken = db.session.execute(select(User.id).where(User.login == login_value)).scalar_one_or_none()
    return jsonify(available=taken is None)


@bp.get("/requests")
def my_requests():
    user, response = _subscriber()
    if response:
        return response
    tickets = db.session.execute(
        tickets_select().where(Request.user_id == user.id).order_by(Request.created_at.desc(), Request.id.desc())
    ).all()
    return render_template("requests.html", tickets=tickets)


@bp.route("/requests/new", methods=["GET", "POST"])
def new_request():
    user, response = _subscriber()
    if response:
        return response
    errors = {}
    form = {"contact_phone": user.phone, "address": "", "apartment": "", "problem": "", "visit_date": ""}
    if request.method == "POST":
        errors, form = validate_ticket(request.form)
        if not errors:
            if not _exists("work_types", form["work_type_id"]):
                errors["work_type_id"] = "Выберите вариант работ."
            if not _exists("payment_types", form["payment_type_id"]):
                errors["payment_type_id"] = "Выберите способ оплаты."
        if not errors:
            new_status = db.session.execute(select(Status).where(Status.code == "new")).scalar_one()
            db.session.add(Request(
                user_id=user.id,
                address=form["address"],
                apartment=form["apartment"],
                contact_phone=form["contact_phone"],
                problem=form["problem"],
                work_type_id=form["work_type_id"],
                visit_date=date.fromisoformat(form["visit_date"]),
                payment_type_id=form["payment_type_id"],
                status_id=new_status.id,
            ))
            db.session.commit()
            flash("Заявка отправлена. Диспетчер увидит её в общем списке.", "success")
            return redirect(url_for("main.my_requests"))
    return render_template(
        "request_new.html",
        errors=errors,
        form=form,
        work_types=db.session.execute(select(WorkType).order_by(WorkType.name)).scalars().all(),
        payment_types=db.session.execute(select(PaymentType).order_by(PaymentType.id)).scalars().all(),
        today=date.today().isoformat(),
    ), (400 if errors else 200)


@bp.get("/admin")
def admin():
    user = current_user()
    if not user:
        return redirect(url_for("main.login"))
    if user.role != "admin":
        abort(403)
    clauses, filters = _filters(request.args)
    count_stmt = (
        select(func.count())
        .select_from(Request)
        .join(User, User.id == Request.user_id)
        .join(WorkType, WorkType.id == Request.work_type_id)
        .join(Status, Status.id == Request.status_id)
    )
    list_stmt = tickets_select()
    if clauses:
        condition = and_(*clauses)
        count_stmt = count_stmt.where(condition)
        list_stmt = list_stmt.where(condition)
    total = db.session.execute(count_stmt).scalar_one()
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = request.args.get("page", 1, type=int) or 1
    page = min(max(page, 1), pages)
    offset = (page - 1) * PER_PAGE
    tickets = db.session.execute(
        list_stmt.order_by(Request.created_at.desc(), Request.id.desc()).limit(PER_PAGE).offset(offset)
    ).all()
    return render_template(
        "admin.html",
        tickets=tickets,
        statuses=db.session.execute(select(Status).order_by(Status.sort_order)).scalars().all(),
        work_types=db.session.execute(select(WorkType).order_by(WorkType.name)).scalars().all(),
        filters=filters,
        page=page,
        pages=pages,
        total=total,
    )


@bp.post("/admin/requests/<int:ticket_id>/status")
def set_status(ticket_id):
    user = current_user()
    if not user:
        return redirect(url_for("main.login"))
    if user.role != "admin":
        abort(403)
    status_id = request.form.get("status_id", type=int)
    if not status_id or not _exists("statuses", status_id):
        flash("Выберите статус из списка.", "error")
    else:
        result = db.session.execute(
            update(Request)
            .where(Request.id == ticket_id)
            .values(status_id=status_id, updated_at=datetime.now())
        )
        db.session.commit()
        if result.rowcount:
            flash(f"Заявка №{ticket_id}: статус изменён.", "success")
        else:
            flash("Заявка не найдена.", "error")
    return redirect(url_for(
        "main.admin",
        q=request.form.get("q", ""),
        status=request.form.get("status", ""),
        work_type=request.form.get("work_type", ""),
        page=request.form.get("page", 1),
    ))


def _home_for_role():
    user = current_user()
    if user and user.role == "admin":
        return redirect(url_for("main.admin"))
    if user:
        return redirect(url_for("main.my_requests"))
    return redirect(url_for("main.home"))


def _subscriber():
    user = current_user()
    if not user:
        return None, redirect(url_for("main.login"))
    if user.role == "admin":
        return None, redirect(url_for("main.admin"))
    return user, None


def _exists(table, row_id):
    model = LOOKUP.get(table)
    if model is None:
        raise ValueError(table)
    return db.session.get(model, row_id) is not None


def _filters(args):
    clauses = []
    status = (args.get("status") or "").strip()
    work_type = (args.get("work_type") or "").strip()
    query = (args.get("q") or "").strip()
    if status:
        clauses.append(Status.code == status)
    if work_type.isdigit():
        clauses.append(Request.work_type_id == int(work_type))
    if query:
        pattern = _like(query)
        clauses.append(or_(
            Request.address.like(pattern, escape="\\"),
            Request.problem.like(pattern, escape="\\"),
            User.full_name.like(pattern, escape="\\"),
            Request.contact_phone.like(pattern, escape="\\"),
            User.login.like(pattern, escape="\\"),
        ))
    return clauses, {"status": status, "work_type": work_type, "q": query}


def _like(text):
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
