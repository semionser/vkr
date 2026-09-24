import re

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user

from app import db
from app.models import User, Group
from app.security import login_limiter

auth_bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")
MIN_PASSWORD_LENGTH = 8


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Защита от подбора пароля
        wait = login_limiter.blocked_for(username)
        if wait:
            minutes = max(1, round(wait / 60))
            flash(f"Слишком много неудачных попыток. Попробуйте через {minutes} мин.", "danger")
            return render_template("auth/login.html"), 429

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            login_limiter.reset(username)
            # Новая сессия после входа (защита от фиксации сессии)
            session.clear()
            session.permanent = True
            login_user(user)
            return redirect(url_for("main.index"))

        login_limiter.fail(username)
        # Одинаковое сообщение для «нет такого логина» и «неверный пароль»
        flash("Неверный логин или пароль.", "danger")

    return render_template("auth/login.html")


def render_register():
    groups = Group.query.order_by(Group.name).all()
    return render_template("auth/register.html", groups=groups)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # Администратор может заводить студентов, остальным вошедшим регистрация не нужна
    if current_user.is_authenticated and current_user.role != "admin":
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower() or None
        password = request.form.get("password", "")
        first_name = request.form.get("first_name", "").strip()[:80]
        last_name = request.form.get("last_name", "").strip()[:80]

        if not all([username, password, first_name, last_name]):
            flash("Заполните обязательные поля.", "danger")
            return render_register()

        if not USERNAME_RE.match(username):
            flash("Логин: 3–40 символов, латинские буквы, цифры, точка, дефис или подчёркивание.", "danger")
            return render_register()

        if len(password) < MIN_PASSWORD_LENGTH:
            flash(f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов.", "danger")
            return render_register()

        if User.query.filter_by(username=username).first():
            flash("Такой логин уже существует.", "danger")
            return render_register()

        if email and User.query.filter_by(email=email).first():
            flash("Пользователь с таким email уже зарегистрирован.", "danger")
            return render_register()

        group_raw = request.form.get("group_id", "").strip()
        group = db.session.get(Group, int(group_raw)) if group_raw.isdigit() else None

        # Через регистрацию можно создать только студента
        user = User(username=username, email=email, first_name=first_name,
                    last_name=last_name, role="student",
                    group_id=group.id if group else None)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        if current_user.is_authenticated:
            flash(f"Студент {username} зарегистрирован.", "success")
            return redirect(url_for("admin.dashboard"))

        flash("Регистрация выполнена. Теперь войдите.", "success")
        return redirect(url_for("auth.login"))

    return render_register()


@auth_bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("main.index"))
