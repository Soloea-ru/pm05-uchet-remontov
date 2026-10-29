import sqlite3
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent.parent


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"])
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
    migration = ROOT / "sql" / "migration_module3.sql"
    if migration.exists():
        db.executescript(migration.read_text(encoding="utf-8"))
    seed_demo(db)
    db.commit()


def _ref(db, sql, value):
    row = db.execute(sql, (value,)).fetchone()
    if row is None:
        raise RuntimeError(f"В справочнике нет значения: {value}")
    return row["id"]


def seed_demo(db):
    people = [
        ("admin", "Admin123!", "Диспетчер Системы", "+7 900 000-00-01", "admin@example.com", "admin"),
        ("demo", "Demo123!", "Петров Илья Сергеевич", "+7 900 111-22-33", "demo@example.com", "user"),
        ("maria", "Maria123!", "Соколова Мария Андреевна", "+7 900 222-33-44", "maria@example.com", "user"),
    ]
    for login, password, full_name, phone, email, role in people:
        db.execute(
            """
            INSERT INTO users (login, password_hash, full_name, phone, email, role)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (login, generate_password_hash(password, method="pbkdf2:sha256"), full_name, phone, email, role),
        )

    def user_id(login):
        return _ref(db, "SELECT id FROM users WHERE login = ?", login)

    def work_id(name):
        return _ref(db, "SELECT id FROM work_types WHERE name = ?", name)

    def pay_id(name):
        return _ref(db, "SELECT id FROM payment_types WHERE name = ?", name)

    def status_id(code):
        return _ref(db, "SELECT id FROM statuses WHERE code = ?", code)

    tickets = [
        ("demo", "ул. Учебная, д. 1", "12", "+7 900 111-22-33",
         "После грозы пропал интернет, индикатор линии на роутере не горит.",
         "Ремонт линии", "2026-11-05", "По факту", "new", "2026-10-29 12:00:00"),
        ("maria", "ул. Садовая, д. 15", "3", "+7 900 222-33-44",
         "Нужно подключить новую квартиру, роутер уже куплен.",
         "Подключение", "2026-11-06", "Оплачено", "new", "2026-10-29 11:00:00"),
        ("demo", "ул. Лабораторная, д. 4", "7", "+7 900 111-22-33",
         "Роутер включается, но сеть не раздаётся на устройства.",
         "Настройка оборудования", "2026-10-31", "Оплачено", "in_progress", "2026-10-28 10:00:00"),
        ("maria", "ул. Центральная, д. 8", "21", "+7 900 222-33-44",
         "Переезд в другую квартиру, прошу перенести подключение.",
         "Перенос адреса", "2026-11-01", "Рассрочка", "in_progress", "2026-10-27 10:00:00"),
        ("demo", "ул. Полевая, д. 9", "1", "+7 900 111-22-33",
         "Кабель в подъезде был перебит, связь уже восстановили.",
         "Ремонт линии", "2026-10-20", "Оплачено", "done", "2026-10-26 10:00:00"),
        ("maria", "ул. Парковая, д. 2", "44", "+7 900 222-33-44",
         "Подключение по заявке выполнено, скорость в норме.",
         "Подключение", "2026-10-18", "По факту", "done", "2026-10-25 10:00:00"),
    ]
    for login, address, apartment, phone, problem, work, visit, payment, status, created in tickets:
        db.execute(
            """
            INSERT INTO requests (
                user_id, address, apartment, contact_phone, problem,
                work_type_id, visit_date, payment_type_id, status_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id(login), address, apartment, phone, problem,
                work_id(work), visit, pay_id(payment), status_id(status), created,
            ),
        )
