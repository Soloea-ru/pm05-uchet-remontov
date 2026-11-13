import os
import re
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select

from app import create_app
from app.config import mysql_uri
from app.models import AdminAction, Request, Status, WorkType, db
from app.validators import validate_admin_ticket, validate_catalog_name, validate_registration, validate_ticket


class ConfigTests(unittest.TestCase):
    def test_database_url_wins_over_mysql_parts(self):
        env = {
            "DATABASE_URL": "mysql+pymysql://a:b@db:3306/app?charset=utf8mb4",
            "MYSQL_USER": "ignored",
            "MYSQL_PASSWORD": "ignored",
            "MYSQL_HOST": "127.0.0.1",
            "MYSQL_PORT": "3306",
            "MYSQL_DATABASE": "svyazservice",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(mysql_uri(), env["DATABASE_URL"])

    def test_mysql_password_is_url_quoted(self):
        env = {
            "DATABASE_URL": "",
            "MYSQL_USER": "svyaz",
            "MYSQL_PASSWORD": "p@ss:w/rd",
            "MYSQL_HOST": "127.0.0.1",
            "MYSQL_PORT": "3306",
            "MYSQL_DATABASE": "svyazservice",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(
                mysql_uri(),
                "mysql+pymysql://svyaz:p%40ss%3Aw%2Frd@127.0.0.1:3306/svyazservice?charset=utf8mb4",
            )


class ValidatorTests(unittest.TestCase):
    def test_registration_requires_every_field(self):
        errors, _cleaned = validate_registration({})
        self.assertIn("login", errors)
        self.assertIn("password", errors)
        self.assertIn("full_name", errors)
        self.assertIn("phone", errors)
        self.assertIn("email", errors)

    def test_registration_accepts_a_full_name(self):
        errors, cleaned = validate_registration({
            "login": "Student",
            "password": "Student123",
            "password2": "Student123",
            "full_name": "Козлов Павел",
            "phone": "+7 900 333-44-55",
            "email": "student@example.com",
        })
        self.assertEqual(errors, {})
        self.assertEqual(cleaned["login"], "student")

    def test_catalog_name_and_admin_ticket_fields(self):
        errors, _cleaned = validate_catalog_name({"name": "А"})
        self.assertIn("name", errors)
        errors, cleaned = validate_admin_ticket({
            "address": "ул. Учебная, д. 10",
            "apartment": "2",
            "contact_phone": "+7 900 333-44-55",
            "problem": "Нет связи второй день подряд.",
            "work_type_id": "1",
            "payment_type_id": "1",
            "visit_date": "2020-01-01",
            "user_id": "2",
            "status_id": "1",
        })
        self.assertEqual(errors, {})
        self.assertEqual(cleaned["user_id"], 2)

    def test_ticket_rejects_a_past_visit(self):
        errors, _cleaned = validate_ticket({
            "address": "ул. Учебная, д. 10",
            "apartment": "2",
            "contact_phone": "+7 900 333-44-55",
            "problem": "Нет связи второй день подряд.",
            "work_type_id": "1",
            "payment_type_id": "1",
            "visit_date": "2020-01-01",
        })
        self.assertIn("visit_date", errors)


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(Path(self.tmp.name) / "test.db"),
            "TESTING": True,
            "SECRET_KEY": "test-secret",
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tmp.cleanup()

    def token(self, path):
        html = self.client.get(path).get_data(as_text=True)
        match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        self.assertIsNotNone(match)
        return match.group(1)

    def login(self, login, password):
        token = self.token("/login")
        return self.client.post("/login", data={
            "csrf_token": token,
            "login": login,
            "password": password,
        }, follow_redirects=True)

    def test_login_error_and_subscriber_isolation(self):
        bad = self.login("demo", "wrong-pass")
        self.assertIn("Неверный логин или пароль.", bad.get_data(as_text=True))

        page = self.login("demo", "Demo123!")
        text = page.get_data(as_text=True)
        self.assertIn("ул. Учебная, д. 1", text)
        self.assertNotIn("ул. Садовая, д. 15", text)
        self.assertEqual(self.client.get("/admin").status_code, 403)

    def test_register_duplicate_login_and_new_ticket(self):
        token = self.token("/register")
        duplicate = self.client.post("/register", data={
            "csrf_token": token,
            "login": "demo",
            "password": "Student123",
            "password2": "Student123",
            "full_name": "Козлов Павел",
            "phone": "+7 900 333-44-55",
            "email": "student@example.com",
        })
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("уже занят", duplicate.get_data(as_text=True))

        token = self.token("/register")
        created = self.client.post("/register", data={
            "csrf_token": token,
            "login": "student",
            "password": "Student123",
            "password2": "Student123",
            "full_name": "Козлов Павел",
            "phone": "+7 900 333-44-55",
            "email": "student@example.com",
        }, follow_redirects=True)
        self.assertIn("Аккаунт создан", created.get_data(as_text=True))

        self.login("student", "Student123")
        token = self.token("/requests/new")
        visit = (date.today() + timedelta(days=3)).isoformat()
        saved = self.client.post("/requests/new", data={
            "csrf_token": token,
            "address": "ул. Новая, д. 5",
            "apartment": "8",
            "contact_phone": "+7 900 333-44-55",
            "problem": "Нужно проверить кабель в новой квартире.",
            "work_type_id": "1",
            "payment_type_id": "1",
            "visit_date": visit,
        }, follow_redirects=True)
        self.assertIn("ул. Новая, д. 5", saved.get_data(as_text=True))
        self.assertIn("Заявка отправлена", saved.get_data(as_text=True))

    def test_admin_filters_pages_and_status(self):
        page = self.login("admin", "Admin123!")
        self.assertIn("Все заявки", page.get_data(as_text=True))
        done = self.client.get("/admin?status=done")
        done_text = done.get_data(as_text=True)
        self.assertIn("ул. Полевая, д. 9", done_text)
        self.assertNotIn("ул. Учебная, д. 1", done_text)

        second = self.client.get("/admin?page=2").get_data(as_text=True)
        self.assertIn("ул. Парковая, д. 2", second)
        first = self.client.get("/admin").get_data(as_text=True)
        self.assertNotIn("ул. Парковая, д. 2", first)

        token = self.token("/admin")
        with self.app.app_context():
            done_id = db.session.execute(select(Status.id).where(Status.code == "done")).scalar_one()
        changed = self.client.post("/admin/requests/1/status", data={
            "csrf_token": token,
            "status_id": done_id,
            "q": "",
            "status": "",
            "work_type": "",
            "page": "1",
        }, follow_redirects=True)
        self.assertIn("статус изменён", changed.get_data(as_text=True))
        with self.app.app_context():
            code = db.session.execute(
                select(Status.code).join(Request, Request.status_id == Status.id).where(Request.id == 1)
            ).scalar_one()
        self.assertEqual(code, "done")

    def test_admin_crud_journal_and_csrf(self):
        self.login("admin", "Admin123!")
        empty = self.client.post("/admin/requests/new", data={
            "csrf_token": self.token("/admin/requests/new"),
            "address": "",
            "apartment": "",
            "contact_phone": "",
            "problem": "",
            "work_type_id": "",
            "payment_type_id": "",
            "visit_date": "",
            "user_id": "",
            "status_id": "",
        })
        self.assertEqual(empty.status_code, 400)
        self.assertIn("Укажите адрес", empty.get_data(as_text=True))

        forbidden = self.client.post("/admin/requests/new", data={
            "address": "ул. Новая, д. 9",
            "apartment": "4",
            "contact_phone": "+7 900 333-44-55",
            "problem": "Проверка CSRF на форме диспетчера.",
            "work_type_id": "1",
            "payment_type_id": "1",
            "visit_date": date.today().isoformat(),
            "user_id": "2",
            "status_id": "1",
        })
        self.assertEqual(forbidden.status_code, 400)

        created = self.client.post("/admin/requests/new", data={
            "csrf_token": self.token("/admin/requests/new"),
            "address": "ул. Журнальная, д. 10",
            "apartment": "4",
            "contact_phone": "+7 900 333-44-55",
            "problem": "Диспетчер создаёт заявку через панель.",
            "work_type_id": "1",
            "payment_type_id": "1",
            "visit_date": "2020-01-01",
            "user_id": "2",
            "status_id": "1",
        }, follow_redirects=True)
        self.assertIn("Заявка создана", created.get_data(as_text=True))
        self.assertIn("ул. Журнальная, д. 10", created.get_data(as_text=True))

        with self.app.app_context():
            ticket_id = db.session.execute(
                select(Request.id).where(Request.address == "ул. Журнальная, д. 10")
            ).scalar_one()

        edited = self.client.post(f"/admin/requests/{ticket_id}/edit", data={
            "csrf_token": self.token(f"/admin/requests/{ticket_id}/edit"),
            "address": "ул. Журнальная, д. 12",
            "apartment": "4",
            "contact_phone": "+7 900 333-44-55",
            "problem": "Диспетчер создаёт заявку через панель.",
            "work_type_id": "1",
            "payment_type_id": "1",
            "visit_date": "2020-01-01",
            "user_id": "2",
            "status_id": "1",
        }, follow_redirects=True)
        self.assertIn("изменена", edited.get_data(as_text=True))
        self.assertIn("ул. Журнальная, д. 12", edited.get_data(as_text=True))

        confirm = self.client.get(f"/admin/requests/{ticket_id}/delete")
        self.assertIn("Удалить заявку", confirm.get_data(as_text=True))
        deleted = self.client.post(f"/admin/requests/{ticket_id}/delete", data={
            "csrf_token": self.token(f"/admin/requests/{ticket_id}/delete"),
        }, follow_redirects=True)
        self.assertIn("удалена", deleted.get_data(as_text=True))
        self.assertNotIn("ул. Журнальная, д. 12", deleted.get_data(as_text=True))

        catalog = self.client.post("/admin/catalogs/work-types/new", data={
            "csrf_token": self.token("/admin/catalogs/work-types/new"),
            "name": "Диагностика",
        }, follow_redirects=True)
        self.assertIn("Запись сохранена", catalog.get_data(as_text=True))
        self.assertIn("Диагностика", catalog.get_data(as_text=True))
        duplicate = self.client.post("/admin/catalogs/work-types/new", data={
            "csrf_token": self.token("/admin/catalogs/work-types/new"),
            "name": "Диагностика",
        })
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("уже заняты", duplicate.get_data(as_text=True))

        with self.app.app_context():
            extra_id = db.session.execute(
                select(WorkType.id).where(WorkType.name == "Диагностика")
            ).scalar_one()
            used_id = db.session.execute(
                select(WorkType.id).where(WorkType.name == "Подключение")
            ).scalar_one()
        blocked = self.client.get(f"/admin/catalogs/work-types/{used_id}/delete", follow_redirects=True)
        self.assertIn("есть заявки", blocked.get_data(as_text=True))
        removed = self.client.post(f"/admin/catalogs/work-types/{extra_id}/delete", data={
            "csrf_token": self.token(f"/admin/catalogs/work-types/{extra_id}/delete"),
        }, follow_redirects=True)
        self.assertIn("удалена", removed.get_data(as_text=True))

        journal = self.client.get("/admin/journal").get_data(as_text=True)
        self.assertIn("Вход в панель диспетчера", journal)
        self.assertIn("Создание", journal)
        self.assertIn("Изменение", journal)
        self.assertIn("Удаление", journal)

        with self.app.app_context():
            actions = db.session.execute(select(AdminAction.action).order_by(AdminAction.id)).scalars().all()
        self.assertIn("login", actions)
        self.assertIn("create", actions)
        self.assertIn("update", actions)
        self.assertIn("delete", actions)

        missing = self.client.get("/admin/requests/999/edit")
        self.assertEqual(missing.status_code, 404)

        self.client.post("/logout", data={"csrf_token": self.token("/admin")})
        as_user = self.login("demo", "Demo123!")
        self.assertEqual(self.client.get("/admin/journal").status_code, 403)
        self.assertNotIn("Журнал действий", as_user.get_data(as_text=True))

    def test_login_check_api(self):
        free = self.client.get("/api/login-available?login=fresh_user").get_json()
        self.assertTrue(free["available"])
        taken = self.client.get("/api/login-available?login=demo").get_json()
        self.assertFalse(taken["available"])


if __name__ == "__main__":
    unittest.main()
