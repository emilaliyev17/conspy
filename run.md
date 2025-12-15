# Локальный запуск

## 1. PostgreSQL

```bash
# macOS
brew install postgresql
brew services start postgresql

# Создать БД
psql -U postgres
CREATE DATABASE financial_consolidator;
\q
```

## 2. Окружение

```bash
cd conspy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Переменные (.env)

Создать файл `.env` в папке `conspy/`:

### Вариант A: DigitalOcean БД (основная)

```
DB_NAME=financial_consolidator
DB_USER=doadmin
DB_PASSWORD=<пароль из DO>
DB_HOST=app-2918ed8a-0d1e-4c36-b8ec-961630fb78c0-do-user-16968811-0.c.db.ondigitalocean.com
DB_PORT=25060
DEBUG=True
SECRET_KEY=any-random-string
```

### Вариант B: Локальная PostgreSQL

```
DATABASE_URL=postgres://postgres:password@localhost:5432/financial_consolidator
DEBUG=True
SECRET_KEY=any-random-string
```

## 4. Миграции и суперюзер

```bash
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
```

## 5. Запуск

```bash
source venv/bin/activate
python manage.py runserver
```

## URL

- Сайт: http://127.0.0.1:8000/
- P&L: http://127.0.0.1:8000/reports/pl/
- Balance Sheet: http://127.0.0.1:8000/reports/bs/
- Админка: http://127.0.0.1:8000/admin/

