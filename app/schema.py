"""
Простое обновление схемы существующей SQLite-базы.

db.create_all() создаёт только отсутствующие таблицы, но не добавляет
новые колонки в уже существующие. Чтобы старая database.db продолжила
работать после добавления групп, перемешивания и т.д., недостающие
колонки добавляются здесь через ALTER TABLE.

Для промышленной эксплуатации вместо этого стоит подключить
Flask-Migrate (Alembic).
"""

from sqlalchemy import inspect, text


# таблица -> {колонка: SQL-определение}
NEW_COLUMNS = {
    "users": {
        "group_id": "INTEGER REFERENCES groups(id) ON DELETE SET NULL",
    },
    "tests": {
        "shuffle_questions": "BOOLEAN NOT NULL DEFAULT 0",
        "shuffle_answers": "BOOLEAN NOT NULL DEFAULT 0",
        "questions_per_attempt": "INTEGER",
        "scoring_mode": "VARCHAR(20) NOT NULL DEFAULT 'strict'",
        "review_mode": "VARCHAR(20) NOT NULL DEFAULT 'after_all'",
    },
    "attempts": {
        "question_order_json": "TEXT",
        "answer_order_json": "TEXT",
    },
}


def upgrade_schema(db):
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())

    with db.engine.begin() as conn:
        for table, columns in NEW_COLUMNS.items():
            if table not in existing_tables:
                continue

            present = {c["name"] for c in inspector.get_columns(table)}

            for name, ddl in columns.items():
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
