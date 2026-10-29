import re
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from app import create_app
from app.db import close_db, get_db
from app.validators import validate_registration, validate_ticket


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
            "DATABASE": str(Path(self.tmp.name) / "test.db"),
            "TESTING": True,
            "SECRET_KEY": "test-secret",
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            close_db()
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
            done_id = get_db().execute("SELECT id FROM statuses WHERE code = 'done'").fetchone()["id"]
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
            code = get_db().execute(
                """
                SELECT s.code FROM requests r
                JOIN statuses s ON s.id = r.status_id
                WHERE r.id = 1
                """
            ).fetchone()["code"]
        self.assertEqual(code, "done")

    def test_login_check_api(self):
        free = self.client.get("/api/login-available?login=fresh_user").get_json()
        self.assertTrue(free["available"])
        taken = self.client.get("/api/login-available?login=demo").get_json()
        self.assertFalse(taken["available"])


if __name__ == "__main__":
    unittest.main()
