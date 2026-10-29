import re
from datetime import date, datetime

LOGIN_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$")
FIO_RE = re.compile(
    r"^[А-ЯЁA-Z][а-яёa-z]+(?:-[А-ЯЁA-Z][а-яёa-z]+)?"
    r"(?:\s+[А-ЯЁA-Z][а-яёa-z]+(?:-[А-ЯЁA-Z][а-яёa-z]+)?){1,2}$"
)
APARTMENT_RE = re.compile(r"^[0-9А-Яа-яA-Za-z\-/]{1,10}$")


def _text(data, key):
    value = data.get(key, "")
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def validate_registration(data):
    errors = {}
    login = _text(data, "login").lower()
    password = data.get("password", "")
    password2 = data.get("password2", "")
    full_name = _text(data, "full_name")
    phone = _text(data, "phone")
    email = _text(data, "email").lower()

    if not login:
        errors["login"] = "Укажите логин."
    elif not LOGIN_RE.match(login):
        errors["login"] = "Логин: 3–32 символа, латиница, цифры и _, с буквы."

    if not isinstance(password, str) or not password.strip():
        errors["password"] = "Укажите пароль."
    elif not re.search(r"[A-Za-zА-Яа-яЁё]", password) or not re.search(r"\d", password) or len(password) < 8:
        errors["password"] = "Пароль: от 8 символов, минимум одна буква и одна цифра."
    elif len(password) > 128:
        errors["password"] = "Пароль слишком длинный."

    if not isinstance(password2, str) or not password2:
        errors["password2"] = "Повторите пароль."
    elif password != password2:
        errors["password2"] = "Пароли не совпадают."

    if not full_name:
        errors["full_name"] = "Укажите фамилию и имя."
    elif not FIO_RE.match(full_name):
        errors["full_name"] = "ФИО: фамилия и имя с заглавной буквы, можно отчество."

    if not phone:
        errors["phone"] = "Укажите телефон."
    elif not PHONE_RE.match(phone):
        errors["phone"] = "Телефон в формате +7 900 000-00-00."

    if not email:
        errors["email"] = "Укажите email."
    elif not EMAIL_RE.match(email) or len(email) > 120:
        errors["email"] = "Введите корректный email."

    cleaned = {
        "login": login,
        "password": password if isinstance(password, str) else "",
        "full_name": full_name,
        "phone": phone,
        "email": email,
    }
    return errors, cleaned


def validate_ticket(data, today=None):
    errors = {}
    today = today or date.today()
    address = _text(data, "address")
    apartment = _text(data, "apartment")
    contact_phone = _text(data, "contact_phone")
    problem = _text(data, "problem")
    work_type_id = _text(data, "work_type_id")
    payment_type_id = _text(data, "payment_type_id")
    visit_raw = _text(data, "visit_date")

    if len(address) < 5:
        errors["address"] = "Укажите адрес: город, улица и дом."
    elif len(address) > 200:
        errors["address"] = "Адрес слишком длинный."

    if not apartment:
        errors["apartment"] = "Укажите квартиру."
    elif not APARTMENT_RE.match(apartment):
        errors["apartment"] = "Квартира: до 10 букв или цифр."

    if not contact_phone:
        errors["contact_phone"] = "Укажите телефон для связи."
    elif not PHONE_RE.match(contact_phone):
        errors["contact_phone"] = "Телефон в формате +7 900 000-00-00."

    if len(problem) < 10:
        errors["problem"] = "Опишите проблему, минимум 10 символов."
    elif len(problem) > 2000:
        errors["problem"] = "Описание слишком длинное."

    if not work_type_id.isdigit():
        errors["work_type_id"] = "Выберите вариант работ."

    if not payment_type_id.isdigit():
        errors["payment_type_id"] = "Выберите способ оплаты."

    visit = None
    if not visit_raw:
        errors["visit_date"] = "Укажите дату визита."
    else:
        try:
            visit = datetime.strptime(visit_raw, "%Y-%m-%d").date()
        except ValueError:
            errors["visit_date"] = "Дата визита указана неверно."
        else:
            if visit < today:
                errors["visit_date"] = "Дата визита не может быть в прошлом."

    cleaned = {
        "address": address,
        "apartment": apartment,
        "contact_phone": contact_phone,
        "problem": problem,
        "work_type_id": int(work_type_id) if work_type_id.isdigit() else None,
        "payment_type_id": int(payment_type_id) if payment_type_id.isdigit() else None,
        "visit_date": visit.isoformat() if visit else visit_raw,
    }
    return errors, cleaned
