# Campus — керування студентами

Простий застосунок українською: Flask, HTML/CSS/JavaScript і PostgreSQL.
Можливості: додавання, редагування, видалення з підтвердженням, пошук за
ім’ям/прізвищем/email, фільтр за групою, пагінація та статистика.
Email обов’язковий, зберігається в нижньому регістрі й має бути унікальним.

## Безпечна передача вихідного коду

Правила агента — `AGENTS.md`, результати аудиту й план ротації —
`SECURITY_AUDIT.md`. Паролі, `.env`, локальні дані та дампи не публікуйте.

```powershell
./.venv/Scripts/python.exe scripts/check_secrets.py
powershell -NoProfile -File scripts/package-source.ps1
```

ZIP створюється в `.local/exports/` лише з файлів `source-manifest.json`.
Нові файли потрібно явно додавати до маніфесту після перевірки.
Якщо Windows блокує `.ps1`, див. опис дозволу лише для окремого процесу
в `SECURITY_AUDIT.md`; системну політику виконання змінювати не потрібно.
Скрипт нічого не завантажує на GitHub. Застосунок без авторизації
не призначений для публічного доступу з реальними даними студентів.

## Поточна конфігурація: PostgreSQL у Docker

Цей розділ описує початкове середовище на порту 5000. Для окремого
середовища розробки на 5001 використовуйте Docker Compose нижче.

Campus використовує контейнер `postgres-dev`, адресу `127.0.0.1:5432`,
базу `campus` і окремого користувача `campus_app` без прав суперкористувача.
Пароль збережено в `.env`; не публікуйте цей файл. База вже створена,
початкова міграція застосована.

Після зупинки застосунку або перезавантаження комп’ютера:

```powershell
docker start postgres-dev
./.venv/Scripts/python.exe run.py
```

Відкрийте **http://127.0.0.1:5000**. Для цієї конфігурації не потрібно
запускати `scripts/local_db.py`: він обслуговує інший PostgreSQL на порту `55432`.
Після зміни `.env` перезапустіть Flask. Якщо в оточенні задано `DATABASE_URL`,
вона має пріоритет над `.env`.

## Альтернативний запуск у Windows без Docker

Потрібні Python 3.11+ і PostgreSQL 14+ (локальний помічник за замовчуванням шукає PostgreSQL 18).
Виконуйте команди в папці проєкту. Активація venv не потрібна.

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe scripts/local_db.py start
./.venv/Scripts/python.exe -m flask --app run db upgrade
./.venv/Scripts/python.exe run.py
```

Відкрийте **http://127.0.0.1:5000**. Реєстр спочатку порожній.

`local_db.py start` створює окремий кластер у `.local/postgres-data`, слухає
тільки `127.0.0.1:55432`, генерує випадковий пароль і створює `.env`, якщо
його ще немає. Наявні служби PostgreSQL не змінює. Повторний запуск зберігає дані.
Для іншої інсталяції передайте `--bin "C:/Program Files/PostgreSQL/17/bin"`.
Пароль зберігається в ігнорованих Git файлах `.local/db-password` та `.env`.

Зупиніть вебсервер через Ctrl+C, а локальну базу командою:

```powershell
./.venv/Scripts/python.exe scripts/local_db.py stop
```

Після перезавантаження комп’ютера повторіть `local_db.py start` і `run.py`.
Помічник бази призначений для локальної розробки, а не для production.

## Використання власного PostgreSQL

Замість `local_db.py` створіть окремого користувача й базу через pgAdmin або psql:

```sql
CREATE ROLE campus_app LOGIN PASSWORD 'replace-with-your-password';
CREATE DATABASE campus OWNER campus_app;
```

Скопіюйте `.env.example` у `.env` (якщо `.env` ще немає), задайте власні параметри:

```dotenv
DATABASE_URL=postgresql+pg8000://campus_app:your-password@127.0.0.1:5432/campus
```

Спеціальні символи пароля в URL потрібно URL-кодувати. Потім виконайте
`flask --app run db upgrade` через Python із venv і запустіть `run.py`.
У Linux/macOS шлях до Python середовища — `.venv/bin/python`.
Змінна `DATABASE_URL` в оточенні має пріоритет над `.env`.

## Структура

```text
app/
  __init__.py        фабрика Flask, розширення та обробка помилок
  models.py          модель Student
  routes.py          REST API та головна сторінка
  templates/         HTML
  static/css/        стилі, включно з мобільною версією
  static/js/         робота з API та діалогами
migrations/          схема БД та її версії
scripts/local_db.py  запуск окремої локальної PostgreSQL
tests/               перевірки API
config.py            конфігурація через .env
run.py               точка запуску
```

## API

| Метод | Шлях | Дія |
|---|---|---|
| GET | `/api/students` | Список, статистика та групи |
| POST | `/api/students` | Створити студента |
| PUT | `/api/students/<id>` | Оновити всі поля студента |
| DELETE | `/api/students/<id>` | Видалити студента |

GET-параметри: `q`, `group`, `page` (від 1), `per_page` (1–100, стандартно 10).
Відповідь: `items`, `total` (після фільтрації), `all_count`, `groups`, `page`, `per_page`.
POST/PUT приймають JSON:

```json
{"first_name":"Олена","last_name":"Коваль","email":"olena@example.com","group":"КН-21"}
```

Коди: 201 — створено, 200 — оновлено/список, 204 — видалено,
400 — некоректні дані, 404 — немає запису, 409 — email уже використовується,
503 — помилка бази даних. Валідація повертає `error` і, за потреби, `fields`.

## Перевірки

```powershell
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m pytest -q --postgres
./.venv/Scripts/python.exe -m flask --app run db check
node --check app/static/js/app.js
```

Стандартні швидкі тести використовують тимчасову SQLite лише для тестів.
`--postgres` використовує `DATABASE_URL` і створює випадкову окрему схему для
кожного тесту; після тесту видаляє лише цю схему. Користувач БД повинен мати право
створювати схеми. Також можна задати `TEST_DATABASE_URL` для окремої тестової БД.
Пошук без урахування регістру кирилиці перевіряється саме на PostgreSQL.
Node потрібен лише для додаткової перевірки синтаксису JavaScript.

## Міграції й доступ

Після зміни моделі створіть міграцію командою
`flask --app run db migrate -m "Describe change"`, перегляньте її та застосуйте
через `flask --app run db upgrade`. Початкова міграція вже включена — повторно
виконувати `db init` не потрібно. [Документація Flask-Migrate](https://flask-migrate.readthedocs.io/en/latest/).

За погодженим обсягом авторизації немає: користувач із доступом до застосунку
може змінювати всі записи. `run.py` запускає сервер лише на локальній адресі,
без debug. Перед публічним розгортанням потрібні авторизація та production WSGI-сервер.

## Ізольоване середовище Docker Compose

Потрібні Docker Desktop у режимі Linux containers, Docker Compose v2.20+
і вільний порт 5001. Локальний Python для запуску контейнерів не потрібен.
Команди виконуйте з кореня цього проєкту.

| Компонент | Адреса / зберігання |
|---|---|
| Новий project | `campus-compose-dev` |
| Вебзастосунок | `http://127.0.0.1:5001` → Gunicorn `web:8000` |
| Нова БД | PostgreSQL 18, `db:5432`, база/роль `campus_dev` |
| Дані нової БД | Volume `campus-compose-dev_db_data` → `/var/lib/postgresql` |
| Секрети | `.local/compose/admin-password` та `app-password` |
| Наявне середовище | `postgres-dev`, `postgres_data`, порт 5432 — не використовується й не змінюється |

PostgreSQL нового середовища не публікує портів на хості й підключена лише
до внутрішньої мережі `campus`. Web додатково має мережу `frontend` для
публікації строго loopback-порту. Авторизації в UI поки немає.
Роль застосунку не суперкористувач, але володіє новою dev-базою для міграцій.
Dockerfile запускає Gunicorn від UID 10001; коренева ФС app-контейнерів read-only.

### Перший запуск і явні міграції

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/init-compose-secrets.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-compose.ps1
```

`Bypass` діє лише на цей процес PowerShell, не змінює системну політику.
Використовуйте після перегляду локальних скриптів; за корпоративних обмежень
застосовуйте погоджений спосіб виконання, не змінюйте GPO.

Генератор не друкує й не змінює наявні секрети. Збережіть
їх разом із локальним середовищем: новий пароль у файлі сам по собі не змінює
пароль в уже ініціалізованій PostgreSQL. Compose secrets тут є файловими
монтуваннями, не шифрованим сховищем; доступ до хоста/Docker слід обмежувати.
Початкова `.env` не копіюється в образ і не передається сервісам.
Compose та CI задають `CAMPUS_LOAD_DOTENV=0`, щоб вимкнути навіть читання `.env`.

Запуск helper є явною командою застосувати міграції **лише нової dev-бази**:
перевірка конфігурації → збірка → зупинка нового web (якщо він уже працює)
→ healthy PostgreSQL → `migrate` із кодом 0 → healthy web.
За помилки наступний крок не виконується. Міграції не запускаються
автоматично entrypoint вебсервера: він лише перевіряє відповідність Alembic head
і відмовляється стартувати на немігрованій/застарілій схемі.

Еквівалентна ручна послідовність (наступний крок лише після успіху попереднього):

```powershell
docker compose -p campus-compose-dev config --quiet
docker compose -p campus-compose-dev build web
docker compose -p campus-compose-dev stop web
docker compose -p campus-compose-dev up -d --wait db
docker compose -p campus-compose-dev --profile tools run --rm migrate
docker compose -p campus-compose-dev up -d --wait web
```

`run --rm` прибирає лише свій одноразовий контейнер міграцій; volume залишається.
Нова БД спочатку порожня: автоматичного імпорту зі старої БД немає.
Ініціалізація ролі через `docker/init-db.sh` відбувається лише для порожнього нового volume.

### Зупинка та повторний запуск зі збереженням даних

```powershell
docker compose -p campus-compose-dev stop web db
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-compose.ps1
```

Не використовуйте `down -v`, `docker volume rm` або команди проти `postgres-dev`.
`stop` зберігає контейнери, volume і записи. Перед майбутніми змінами міграцій
потрібні перегляд та резервна копія; для первинної порожньої dev-бази імпорт не потрібен.

### Перевірки нового середовища

```powershell
docker compose -p campus-compose-dev ps
docker compose -p campus-compose-dev exec -T web python -m pytest -q -p no:cacheprovider
docker compose -p campus-compose-dev exec -T web python -m pytest -q --postgres -p no:cacheprovider
docker compose -p campus-compose-dev exec -T web python -m flask --app run db current
docker compose -p campus-compose-dev exec -T web python -m flask --app run db check
node --check app/static/js/app.js
```

SQLite працює в пам’яті. PostgreSQL-тести створюють і прибирають власні
випадкові схеми лише в новій dev-базі. Прапорець `--postgres` надає
`TEST_DATABASE_URL` пріоритет над конфігурацією застосунку, якщо він явно заданий.
`DB_PASSWORD_FILE` разом із `DB_HOST/DB_PORT/DB_NAME/DB_USER` вибирає файлове
підключення контейнера; інакше зберігається попередня поведінка `DATABASE_URL`.

## GitHub Actions

Workflow `.github/workflows/ci.yml` призначений для `rzikratyj-student/university-app`:
push у `main`, pull request до `main` і ручний `workflow_dispatch`.

- `sqlite-and-javascript`: Python 3.12, SQLite pytest, Node 22 syntax check,
  сканер секретів і `docker compose config --quiet`.
- `postgres`: Python 3.12, окрема PostgreSQL 18, застосування початкової
  міграції, перевірка відповідності схеми та pytest.

Збережених GitHub Secrets **не потрібно**. `scripts/ci_postgres.py` генерує
одноразовий пароль, записує його в тимчасовий файл і передає через `_FILE`.
Пароль не потрапляє до аргументів команд, workflow-файлу чи виводу; підключення
тестів передається через середовище дочірнього процесу, його вивід редагується.
Контейнер має випадкове ім’я, нові дані у tmpfs і випадковий loopback-порт
runner. У `finally` видаляється лише цей створений контейнер; секрет прибирається.
За примусового скасування job остаточне прибирання забезпечує тимчасовий hosted runner.

CI не звертається до локальних `.env`, `postgres-dev`, `postgres_data` чи dev-volume.
Оскільки довготривалих секретів немає, обидва jobs можуть працювати на PR із forks
(із типовими правилами погодження GitHub для сторонніх внесків).
Використано `pull_request`, не `pull_request_target`; права — лише `contents: read`,
checkout не зберігає облікові дані. Actions зафіксовано за commit SHA.
Workflow нічого не публікує й не розгортає.

Локальна перевірка того самого PostgreSQL CI-helper (потрібні Docker і Python-залежності):

```powershell
./.venv/Scripts/python.exe scripts/ci_postgres.py
```

Це окремий одноразовий тест, а не робота з dev-базою. Фактичний статус Actions
на GitHub з’явиться лише після окремо погодженого push; локальний запуск не є
підтвердженням віддаленого workflow run.
