from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from pathlib import Path

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    base_dir = Path(__file__).resolve().parent.parent
    app.config["SECRET_KEY"] = "change-this-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{base_dir / 'database.db'}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

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
        db.create_all()

    return app
