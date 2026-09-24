import os
from datetime import timedelta
from pathlib import Path

from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Войдите, чтобы открыть эту страницу."
login_manager.login_message_category = "warning"


def format_number(value):
    """3.0 -> '3', 2.5 -> '2.5', 1.333 -> '1.33' (для баллов)."""
    if value is None:
        return "0"
    value = round(float(value), 2)
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def load_env_file(path):
    """Простая загрузка переменных из файла .env (без сторонних библиотек)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)


def create_app(config=None):
    base_dir = Path(__file__).resolve().parent.parent
    load_env_file(base_dir / ".env")

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        instance_path=str(base_dir / "instance"),
    )

    from app.security import init_security, load_secret_key

    app.config.update(
        SECRET_KEY=load_secret_key(app.instance_path),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", f"sqlite:///{base_dir / 'database.db'}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,

        # Cookie сессии недоступна из JavaScript и не уходит на чужие сайты
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # На сервере с HTTPS включается переменной окружения HTTPS=1
        SESSION_COOKIE_SECURE=env_flag("HTTPS"),
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=env_flag("HTTPS"),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),

        # Ограничение размера запроса (защита от слишком больших форм)
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,

        CSRF_ENABLED=True,
    )

    if config:
        app.config.update(config)

    db.init_app(app)
    login_manager.init_app(app)
    init_security(app)

    app.jinja_env.filters["num"] = format_number

    from app.models import User
    from app.auth.routes import auth_bp
    from app.student.routes import student_bp
    from app.teacher.routes import teacher_bp
    from app.admin.routes import admin_bp
    from app.main.routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(teacher_bp, url_prefix="/teacher")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def http_error(error):
        return render_template("error.html", error=error), error.code

    with app.app_context():
        from app.schema import upgrade_schema

        db.create_all()
        upgrade_schema(db)

    return app
