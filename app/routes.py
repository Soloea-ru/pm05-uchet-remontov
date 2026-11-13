import secrets
from datetime import date

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from .auth import current_user
from .journal import log_admin
from .models import PaymentType, Request, Status, User, WorkType, db, exists, tickets_select
from .validators import LOGIN_RE, validate_registration, validate_ticket

bp = Blueprint("main", __name__)


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
            if user.role == "admin":
                log_admin(user, "login", "user", user.id, "Вход в панель диспетчера")
                db.session.commit()
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
            if not exists(WorkType, form["work_type_id"]):
                errors["work_type_id"] = "Выберите вариант работ."
            if not exists(PaymentType, form["payment_type_id"]):
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


def _home_for_role():
    user = current_user()
    if user and user.role == "admin":
        return redirect(url_for("admin.tickets"))
    if user:
        return redirect(url_for("main.my_requests"))
    return redirect(url_for("main.home"))


def _subscriber():
    user = current_user()
    if not user:
        return None, redirect(url_for("main.login"))
    if user.role == "admin":
        return None, redirect(url_for("admin.tickets"))
    return user, None
