-- Модуль 3. Индексы для сценариев списка, фильтра и карточки абонента.
-- Безопасно запускать повторно: CREATE INDEX IF NOT EXISTS.
-- Новая установка выполняет этот файл сразу после sql/schema.sql.

PRAGMA foreign_keys = ON;

CREATE INDEX IF NOT EXISTS idx_requests_user_id ON requests(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_status_id ON requests(status_id);
CREATE INDEX IF NOT EXISTS idx_requests_work_type_id ON requests(work_type_id);
CREATE INDEX IF NOT EXISTS idx_requests_visit_date ON requests(visit_date);
CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests(created_at);
CREATE INDEX IF NOT EXISTS idx_requests_status_created ON requests(status_id, created_at DESC);
