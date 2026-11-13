-- ИС «СвязьСервис»: учёт заявок на ремонт и подключение.
-- Схема MySQL 8 (utf8mb4). Учебные пользователи и заявки добавляет приложение при пустой базе.
-- Вторичные индексы: sql/migration_module3.sql.
-- Связи Crow's Foot: users 1—N requests; справочники 1—N requests.
-- Журнал действий администратора: users 1—N admin_actions.
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS users (
    id INT NOT NULL AUTO_INCREMENT,
    login VARCHAR(32) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(32) NOT NULL,
    email VARCHAR(120) NOT NULL,
    role VARCHAR(16) NOT NULL DEFAULT 'user',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_login (login),
    CONSTRAINT ck_users_login CHECK (CHAR_LENGTH(login) >= 3),
    CONSTRAINT ck_users_password CHECK (CHAR_LENGTH(password_hash) > 0),
    CONSTRAINT ck_users_full_name CHECK (CHAR_LENGTH(TRIM(full_name)) >= 5),
    CONSTRAINT ck_users_phone CHECK (CHAR_LENGTH(TRIM(phone)) >= 10),
    CONSTRAINT ck_users_email CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT ck_users_role CHECK (role IN ('user', 'admin'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS work_types (
    id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(80) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_work_types_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payment_types (
    id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(80) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_payment_types_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS statuses (
    id INT NOT NULL AUTO_INCREMENT,
    code VARCHAR(32) NOT NULL,
    name VARCHAR(80) NOT NULL,
    sort_order INT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_statuses_code (code),
    UNIQUE KEY uq_statuses_name (name),
    UNIQUE KEY uq_statuses_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS requests (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    address VARCHAR(200) NOT NULL,
    apartment VARCHAR(10) NOT NULL,
    contact_phone VARCHAR(32) NOT NULL,
    problem TEXT NOT NULL,
    work_type_id INT NOT NULL,
    visit_date DATE NOT NULL,
    payment_type_id INT NOT NULL,
    status_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_requests_address CHECK (CHAR_LENGTH(TRIM(address)) >= 5),
    CONSTRAINT ck_requests_apartment CHECK (CHAR_LENGTH(TRIM(apartment)) >= 1),
    CONSTRAINT ck_requests_phone CHECK (CHAR_LENGTH(TRIM(contact_phone)) >= 10),
    CONSTRAINT ck_requests_problem CHECK (CHAR_LENGTH(TRIM(problem)) >= 10),
    CONSTRAINT fk_requests_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_requests_work_type FOREIGN KEY (work_type_id) REFERENCES work_types (id),
    CONSTRAINT fk_requests_payment FOREIGN KEY (payment_type_id) REFERENCES payment_types (id),
    CONSTRAINT fk_requests_status FOREIGN KEY (status_id) REFERENCES statuses (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS admin_actions (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NULL,
    login VARCHAR(32) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(16) NOT NULL,
    entity_type VARCHAR(32) NOT NULL,
    entity_id INT NULL,
    summary VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    KEY idx_admin_actions_created_at (created_at),
    KEY idx_admin_actions_user_id (user_id),
    KEY idx_admin_actions_entity (entity_type, entity_id),
    CONSTRAINT ck_admin_actions_action CHECK (action IN ('login', 'create', 'update', 'delete')),
    CONSTRAINT ck_admin_actions_login CHECK (CHAR_LENGTH(TRIM(login)) >= 1),
    CONSTRAINT ck_admin_actions_summary CHECK (CHAR_LENGTH(TRIM(summary)) >= 1),
    CONSTRAINT fk_admin_actions_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Справочники, учебные пользователи и заявки добавляет приложение при пустой базе
-- (кириллица в init-скриптах Docker MySQL приходит в latin1 и портит названия).
