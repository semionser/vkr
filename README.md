# Student Testing System — Flask + SQLite

## Исправленная версия

### Запуск в Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python run.py
```

Открыть в браузере:

http://127.0.0.1:5000/

### Учётные записи

Администратор:
- login: `admin`
- password: `admin123`

Преподаватель:
- login: `teacher`
- password: `teacher123`

Студент регистрируется через `/auth/register`.

## Важно

Папки `templates` и `static` находятся внутри `app`, поэтому Flask корректно находит шаблоны и CSS.

Перед использованием в ВКР замените SECRET_KEY и добавьте CSRF-защиту, миграции БД и полноценную серверную проверку времени теста.
