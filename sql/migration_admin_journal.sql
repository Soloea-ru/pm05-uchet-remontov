-- Журнал действий диспетчера. Для базы, созданной до этой таблицы.
-- Новая установка берёт таблицу из sql/schema.sql. Повторный запуск безопасен.

SET NAMES utf8mb4;

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
