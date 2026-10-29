import secrets
from datetime import date

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .validators import LOGIN_RE, validate_registration, validate_ticket

bp = Blueprint("main", __name__)

PER_PAGE = 5

TICKET_SQL = """
SELECT r.id, r.address, r.apartment, r.contact_phone, r.problem,
       r.visit_date, r.created_at, r.updated_at, r.user_id,
       u.full_name, u.login AS user_login,
       wt.name AS work_type, pt.name AS payment_type,
       s.name AS status_name, s.code AS status_code, s.id AS status_id
FROM requests r
JOIN users u ON u.id = r.user_id
JOIN work_types wt ON wt.id = r.work_type_id
JOIN payment_types pt ON pt.id = r.payment_type_id
JOIN statuses s ON s.id = r.status_id
"""


def inject_template_context():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return {"csrf": session["csrf"], "me": current_user()}


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


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
            db = get_db()
            taken = db.execute(
                "SELECT id FROM users WHERE login = ?", (cleaned["login"],)
            ).fetchone()
            if taken:
                errors["login"] = "Такой логин уже занят."
            else:
                db.execute(
                    """
                    INSERT INTO users (login, password_hash, full_name, phone, email, role)
                    VALUES (?, ?, ?, ?, ?, 'user')
                    """,
                    (
                        cleaned["login"],
                        generate_password_hash(cleaned["password"], method="pbkdf2:sha256"),
                        cleaned["full_name"],
                        cleaned["phone"],
                        cleaned["email"],
                    ),
                )
                db.commit()
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
            user = get_db().execute("SELECT * FROM users WHERE login = ?", (form_login,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            error = "Неверный логин или пароль."
        else:
            session.clear()
            session["user_id"] = user["id"]
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
    taken = get_db().execute("SELECT id FROM users WHERE login = ?", (login_value,)).fetchone()
    return jsonify(available=taken is None)


@bp.get("/requests")
def my_requests():
    user, response = _subscriber()
    if response:
        return response
    tickets = get_db().execute(
        TICKET_SQL + " WHERE r.user_id = ? ORDER BY r.created_at DESC, r.id DESC",
        (user["id"],),
    ).fetchall()
    return render_template("requests.html", tickets=tickets)


@bp.route("/requests/new", methods=["GET", "POST"])
def new_request():
    user, response = _subscriber()
    if response:
        return response
    db = get_db()
    errors = {}
    form = {"contact_phone": user["phone"], "address": "", "apartment": "", "problem": "", "visit_date": ""}
    if request.method == "POST":
        errors, form = validate_ticket(request.form)
        if not errors:
            if not _exists(db, "work_types", form["work_type_id"]):
                errors["work_type_id"] = "Выберите вариант работ."
            if not _exists(db, "payment_types", form["payment_type_id"]):
                errors["payment_type_id"] = "Выберите способ оплаты."
        if not errors:
            new_status = db.execute("SELECT id FROM statuses WHERE code = 'new'").fetchone()
            db.execute(
                """
                INSERT INTO requests (
                    user_id, address, apartment, contact_phone, problem,
                    work_type_id, visit_date, payment_type_id, status_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"], form["address"], form["apartment"], form["contact_phone"],
                    form["problem"], form["work_type_id"], form["visit_date"],
                    form["payment_type_id"], new_status["id"],
                ),
            )
            db.commit()
            flash("Заявка отправлена. Диспетчер увидит её в общем списке.", "success")
            return redirect(url_for("main.my_requests"))
    return render_template(
        "request_new.html",
        errors=errors,
        form=form,
        work_types=db.execute("SELECT id, name FROM work_types ORDER BY name").fetchall(),
        payment_types=db.execute("SELECT id, name FROM payment_types ORDER BY id").fetchall(),
        today=date.today().isoformat(),
    ), (400 if errors else 200)


@bp.get("/admin")
def admin():
    user = current_user()
    if not user:
        return redirect(url_for("main.login"))
    if user["role"] != "admin":
        abort(403)
    db = get_db()
    where, params, filters = _filters(request.args)
    total = db.execute(f"SELECT COUNT(*) AS n FROM requests r JOIN users u ON u.id = r.user_id JOIN work_types wt ON wt.id = r.work_type_id JOIN statuses s ON s.id = r.status_id {where}", params).fetchone()["n"]
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = request.args.get("page", 1, type=int) or 1
    page = min(max(page, 1), pages)
    offset = (page - 1) * PER_PAGE
    tickets = db.execute(
        TICKET_SQL + f" {where} ORDER BY r.created_at DESC, r.id DESC LIMIT ? OFFSET ?",
        (*params, PER_PAGE, offset),
    ).fetchall()
    return render_template(
        "admin.html",
        tickets=tickets,
        statuses=db.execute("SELECT id, code, name FROM statuses ORDER BY sort_order").fetchall(),
        work_types=db.execute("SELECT id, name FROM work_types ORDER BY name").fetchall(),
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
    if user["role"] != "admin":
        abort(403)
    db = get_db()
    status_id = request.form.get("status_id", type=int)
    if not status_id or not _exists(db, "statuses", status_id):
        flash("Выберите статус из списка.", "error")
    else:
        updated = db.execute(
            """
            UPDATE requests
            SET status_id = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (status_id, ticket_id),
        )
        db.commit()
        if updated.rowcount:
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
    if user and user["role"] == "admin":
        return redirect(url_for("main.admin"))
    if user:
        return redirect(url_for("main.my_requests"))
    return redirect(url_for("main.home"))


def _subscriber():
    user = current_user()
    if not user:
        return None, redirect(url_for("main.login"))
    if user["role"] == "admin":
        return None, redirect(url_for("main.admin"))
    return user, None


def _exists(db, table, row_id):
    if table not in {"work_types", "payment_types", "statuses"}:
        raise ValueError(table)
    return db.execute(f"SELECT id FROM {table} WHERE id = ?", (row_id,)).fetchone()


def _filters(args):
    clauses = []
    params = []
    status = (args.get("status") or "").strip()
    work_type = (args.get("work_type") or "").strip()
    query = (args.get("q") or "").strip()
    if status:
        clauses.append("s.code = ?")
        params.append(status)
    if work_type.isdigit():
        clauses.append("r.work_type_id = ?")
        params.append(int(work_type))
    if query:
        pattern = _like(query)
        clauses.append(
            "(r.address LIKE ? ESCAPE '\\' OR r.problem LIKE ? ESCAPE '\\' "
            "OR u.full_name LIKE ? ESCAPE '\\' OR r.contact_phone LIKE ? ESCAPE '\\' "
            "OR u.login LIKE ? ESCAPE '\\')"
        )
        params.extend([pattern] * 5)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params, {"status": status, "work_type": work_type, "q": query}


def _like(text):
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
