-- ИС «СвязьСервис»: учёт заявок на ремонт и подключение.
-- Итоговая логическая схема (модули 1 и 3).
-- Вторичные индексы добавляет sql/migration_module3.sql.
-- Связи Crow's Foot: users 1—N requests; справочники 1—N requests.

PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE CHECK (length(login) >= 3),
    password_hash TEXT NOT NULL CHECK (length(password_hash) > 0),
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) >= 5),
    phone TEXT NOT NULL CHECK (length(trim(phone)) >= 10),
    email TEXT NOT NULL CHECK (email LIKE '%_@_%._%'),
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE work_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE payment_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL UNIQUE
);

CREATE TABLE requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    address TEXT NOT NULL CHECK (length(trim(address)) >= 5),
    apartment TEXT NOT NULL CHECK (length(trim(apartment)) >= 1),
    contact_phone TEXT NOT NULL CHECK (length(trim(contact_phone)) >= 10),
    problem TEXT NOT NULL CHECK (length(trim(problem)) >= 10),
    work_type_id INTEGER NOT NULL REFERENCES work_types(id),
    visit_date TEXT NOT NULL CHECK (length(visit_date) = 10),
    payment_type_id INTEGER NOT NULL REFERENCES payment_types(id),
    status_id INTEGER NOT NULL REFERENCES statuses(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT
);

INSERT INTO work_types (name) VALUES
    ('Подключение'),
    ('Ремонт линии'),
    ('Настройка оборудования'),
    ('Перенос адреса');

INSERT INTO payment_types (name) VALUES
    ('Оплачено'),
    ('Рассрочка'),
    ('По факту');

INSERT INTO statuses (code, name, sort_order) VALUES
    ('new', 'Новая', 1),
    ('in_progress', 'В работе', 2),
    ('done', 'Выполнена', 3);
