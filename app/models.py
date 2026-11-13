from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, func, select
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(Integer, primary_key=True)
    login = db.Column(String(32), unique=True, nullable=False)
    password_hash = db.Column(String(255), nullable=False)
    full_name = db.Column(String(120), nullable=False)
    phone = db.Column(String(32), nullable=False)
    email = db.Column(String(120), nullable=False)
    role = db.Column(String(16), nullable=False, default="user")
    created_at = db.Column(DateTime, nullable=False, default=datetime.now)
    requests = relationship("Request", back_populates="user")
    actions = relationship("AdminAction", back_populates="user")


class WorkType(db.Model):
    __tablename__ = "work_types"

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(80), unique=True, nullable=False)
    requests = relationship("Request", back_populates="work_type_row")


class PaymentType(db.Model):
    __tablename__ = "payment_types"

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(80), unique=True, nullable=False)
    requests = relationship("Request", back_populates="payment_type_row")


class Status(db.Model):
    __tablename__ = "statuses"

    id = db.Column(Integer, primary_key=True)
    code = db.Column(String(32), unique=True, nullable=False)
    name = db.Column(String(80), unique=True, nullable=False)
    sort_order = db.Column(Integer, unique=True, nullable=False)
    requests = relationship("Request", back_populates="status_row")


class Request(db.Model):
    __tablename__ = "requests"
    __table_args__ = (
        Index("idx_requests_user_id", "user_id"),
        Index("idx_requests_status_id", "status_id"),
        Index("idx_requests_work_type_id", "work_type_id"),
        Index("idx_requests_visit_date", "visit_date"),
        Index("idx_requests_created_at", "created_at"),
        Index("idx_requests_status_created", "status_id", "created_at"),
    )

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    address = db.Column(String(200), nullable=False)
    apartment = db.Column(String(10), nullable=False)
    contact_phone = db.Column(String(32), nullable=False)
    problem = db.Column(Text, nullable=False)
    work_type_id = db.Column(Integer, ForeignKey("work_types.id"), nullable=False)
    visit_date = db.Column(Date, nullable=False)
    payment_type_id = db.Column(Integer, ForeignKey("payment_types.id"), nullable=False)
    status_id = db.Column(Integer, ForeignKey("statuses.id"), nullable=False)
    created_at = db.Column(DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(DateTime)

    user = relationship("User", back_populates="requests")
    work_type_row = relationship("WorkType", back_populates="requests")
    payment_type_row = relationship("PaymentType", back_populates="requests")
    status_row = relationship("Status", back_populates="requests")


class AdminAction(db.Model):
    __tablename__ = "admin_actions"
    __table_args__ = (
        Index("idx_admin_actions_created_at", "created_at"),
        Index("idx_admin_actions_user_id", "user_id"),
        Index("idx_admin_actions_entity", "entity_type", "entity_id"),
    )

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    login = db.Column(String(32), nullable=False)
    created_at = db.Column(DateTime, nullable=False, default=datetime.now)
    action = db.Column(String(16), nullable=False)
    entity_type = db.Column(String(32), nullable=False)
    entity_id = db.Column(Integer)
    summary = db.Column(String(255), nullable=False)
    user = relationship("User", back_populates="actions")


def exists(model, row_id):
    return row_id is not None and db.session.get(model, row_id) is not None


def tickets_select():
    return (
        select(
            Request.id,
            Request.address,
            Request.apartment,
            Request.contact_phone,
            Request.problem,
            Request.visit_date,
            Request.created_at,
            Request.updated_at,
            Request.user_id,
            User.full_name,
            User.login.label("user_login"),
            WorkType.name.label("work_type"),
            PaymentType.name.label("payment_type"),
            Status.name.label("status_name"),
            Status.code.label("status_code"),
            Request.status_id,
        )
        .select_from(Request)
        .join(User, User.id == Request.user_id)
        .join(WorkType, WorkType.id == Request.work_type_id)
        .join(PaymentType, PaymentType.id == Request.payment_type_id)
        .join(Status, Status.id == Request.status_id)
    )


def init_db():
    db.create_all()
    seed_demo()


def seed_demo():
    if db.session.execute(select(func.count()).select_from(WorkType)).scalar() == 0:
        db.session.add_all([
            WorkType(name="Подключение"),
            WorkType(name="Ремонт линии"),
            WorkType(name="Настройка оборудования"),
            WorkType(name="Перенос адреса"),
        ])
    if db.session.execute(select(func.count()).select_from(PaymentType)).scalar() == 0:
        db.session.add_all([
            PaymentType(name="Оплачено"),
            PaymentType(name="Рассрочка"),
            PaymentType(name="По факту"),
        ])
    if db.session.execute(select(func.count()).select_from(Status)).scalar() == 0:
        db.session.add_all([
            Status(code="new", name="Новая", sort_order=1),
            Status(code="in_progress", name="В работе", sort_order=2),
            Status(code="done", name="Выполнена", sort_order=3),
        ])
    db.session.flush()

    if db.session.execute(select(func.count()).select_from(User)).scalar() > 0:
        db.session.commit()
        return

    people = [
        ("admin", "Admin123!", "Диспетчер Системы", "+7 900 000-00-01", "admin@example.com", "admin"),
        ("demo", "Demo123!", "Петров Илья Сергеевич", "+7 900 111-22-33", "demo@example.com", "user"),
        ("maria", "Maria123!", "Соколова Мария Андреевна", "+7 900 222-33-44", "maria@example.com", "user"),
    ]
    for login, password, full_name, phone, email, role in people:
        db.session.add(User(
            login=login,
            password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
            full_name=full_name,
            phone=phone,
            email=email,
            role=role,
        ))
    db.session.flush()

    def user_id(login):
        return db.session.execute(select(User.id).where(User.login == login)).scalar_one()

    def work_id(name):
        return db.session.execute(select(WorkType.id).where(WorkType.name == name)).scalar_one()

    def pay_id(name):
        return db.session.execute(select(PaymentType.id).where(PaymentType.name == name)).scalar_one()

    def status_id(code):
        return db.session.execute(select(Status.id).where(Status.code == code)).scalar_one()

    tickets = [
        ("demo", "ул. Учебная, д. 1", "12", "+7 900 111-22-33",
         "После грозы пропал интернет, индикатор линии на роутере не горит.",
         "Ремонт линии", "2026-11-05", "По факту", "new", datetime(2026, 10, 29, 12, 0, 0)),
        ("maria", "ул. Садовая, д. 15", "3", "+7 900 222-33-44",
         "Нужно подключить новую квартиру, роутер уже куплен.",
         "Подключение", "2026-11-06", "Оплачено", "new", datetime(2026, 10, 29, 11, 0, 0)),
        ("demo", "ул. Лабораторная, д. 4", "7", "+7 900 111-22-33",
         "Роутер включается, но сеть не раздаётся на устройства.",
         "Настройка оборудования", "2026-10-31", "Оплачено", "in_progress", datetime(2026, 10, 28, 10, 0, 0)),
        ("maria", "ул. Центральная, д. 8", "21", "+7 900 222-33-44",
         "Переезд в другую квартиру, прошу перенести подключение.",
         "Перенос адреса", "2026-11-01", "Рассрочка", "in_progress", datetime(2026, 10, 27, 10, 0, 0)),
        ("demo", "ул. Полевая, д. 9", "1", "+7 900 111-22-33",
         "Кабель в подъезде был перебит, связь уже восстановили.",
         "Ремонт линии", "2026-10-20", "Оплачено", "done", datetime(2026, 10, 26, 10, 0, 0)),
        ("maria", "ул. Парковая, д. 2", "44", "+7 900 222-33-44",
         "Подключение по заявке выполнено, скорость в норме.",
         "Подключение", "2026-10-18", "По факту", "done", datetime(2026, 10, 25, 10, 0, 0)),
    ]
    for login, address, apartment, phone, problem, work, visit, payment, status, created in tickets:
        db.session.add(Request(
            user_id=user_id(login),
            address=address,
            apartment=apartment,
            contact_phone=phone,
            problem=problem,
            work_type_id=work_id(work),
            visit_date=date.fromisoformat(visit),
            payment_type_id=pay_id(payment),
            status_id=status_id(status),
            created_at=created,
        ))
    db.session.commit()
