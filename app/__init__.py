from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from pathlib import Path

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def format_number(value):
    """3.0 -> '3', 2.5 -> '2.5', 1.333 -> '1.33' (для баллов)."""
    if value is None:
        return "0"
    value = round(float(value), 2)
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    base_dir = Path(__file__).resolve().parent.parent
    app.config["SECRET_KEY"] = "change-this-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{base_dir / 'database.db'}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if config:
        app.config.update(config)

    db.init_app(app)
    login_manager.init_app(app)

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

    with app.app_context():
        from app.schema import upgrade_schema

        db.create_all()
        upgrade_schema(db)

    return app
