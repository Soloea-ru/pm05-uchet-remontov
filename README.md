# СвязьСервис

Учебная информационная система для ПМ.05: учёт заявок на ремонт и подключение. Абонент регистрируется, оставляет заявку и смотрит только свои записи. Диспетчер видит общий список, фильтрует его и меняет статус.

Предметная область — заявки связиста: адрес, квартира, описание, вариант работ, дата визита и оплата. В базе нет данных реальных абонентов, только учебные примеры.

## База: MySQL + SQLAlchemy

Приложение ходит в **MySQL** через **Flask-SQLAlchemy**. Логин и пароль базы в git не кладём: только переменные окружения или файл `.env` (его нет в репозитории, образец — `.env.example`).

### 1. Поднять MySQL (Docker)

```powershell
copy .env.example .env
docker compose up -d
```

Compose создаёт базу `svyazservice`, пользователя `svyaz` и пароль из `MYSQL_PASSWORD` (в примере — `svyaz`, только для локальной машины). Схема и индексы подхватываются из `sql/schema.sql` и `sql/migration_module3.sql`.

Без Docker — свой сервер MySQL 8, та же схема:

```sql
CREATE DATABASE svyazservice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Затем выполните `sql/schema.sql` и `sql/migration_module3.sql` в этой базе.

### 2. Указать приложению, куда подключаться

В `.env` (или в переменных среды Windows / Linux):

```
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=svyaz
MYSQL_PASSWORD=svyaz
MYSQL_DATABASE=svyazservice
```

Либо одна строка:

```
DATABASE_URL=mysql+pymysql://svyaz:ПАРОЛЬ@127.0.0.1:3306/svyazservice?charset=utf8mb4
```

`DATABASE_URL` важнее отдельных `MYSQL_*`. Если база пустая, при первом запуске приложение само добавит справочники и учебные заявки.

### 3. Запуск сайта

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\make_images.py
.\.venv\Scripts\python.exe run.py
```

Откройте http://127.0.0.1:5000

## Проверки

Автотесты **не требуют MySQL**: они поднимают временный SQLite через `SQLALCHEMY_DATABASE_URI` в тестовом конфиге.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

## Учебные входы

| Логин | Пароль | Кто |
| --- | --- | --- |
| admin | Admin123! | диспетчер |
| demo | Demo123! | абонент Петров Илья Сергеевич |
| maria | Maria123! | абонент Соколова Мария Андреевна |

## Сущности

- `users` — логин, хеш пароля, ФИО, телефон, email, роль `user` или `admin`.
- `requests` — заявка абонента: адрес, квартира, телефон связи, проблема, дата визита.
- `work_types` — вариант работ: подключение, ремонт линии, настройка оборудования, перенос адреса.
- `payment_types` — оплачено, рассрочка, по факту.
- `statuses` — новая, в работе, выполнена.

Связи: один пользователь — много заявок; каждый справочник — много заявок. Диаграмма Crow's Foot: `docs/er.svg`.

## Сценарии

1. Регистрация с проверкой логина, пароля, ФИО, телефона и email. Логин уникален.
2. Вход. Ошибка логина или пароля не говорит, какое поле неверно. Со страницы входа есть переход на регистрацию и обратно.
3. Абонент видит свои заявки и создаёт новую. Чужие записи ему не показываются.
4. Диспетчер открывает общий список, фильтрует по статусу, варианту и строке поиска, листает страницы и меняет статус. После сохранения появляется уведомление.

## Где лежат результаты модулей

| Модуль | Файлы |
| --- | --- |
| 1. База и сценарии | `sql/schema.sql`, `docs/er.svg`, `app/`, `templates/` |
| 2. Дизайн | `static/css/style.css`, `static/js/main.js`, `static/img/`, `docs/ui-guide.md`, `docs/images/` |
| 3. Доработка | `sql/migration_module3.sql`, `docs/checklist.md` |
| 4. MySQL и ORM | `app/config.py`, `app/models.py`, `docker-compose.yml`, `.env.example` |

Слайдер на главной: 4 кадра 1200×675, автопрокрутка 3 секунды, кнопки назад и вперёд. Макет сжимается под ширину 390px.

## Стек

Python, Flask, Flask-SQLAlchemy, MySQL, HTML, CSS и JavaScript без отдельной библиотеки интерфейса. Пароли хранятся как хеш PBKDF2, не открытым текстом. Учётные данные MySQL — только из окружения, не из репозитория.
