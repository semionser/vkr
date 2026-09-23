from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            return redirect(url_for("main.index"))
        flash("Неверный логин или пароль.", "danger")
    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip() or None
        password = request.form.get("password", "")
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        if not all([username, password, first_name, last_name]):
            flash("Заполните обязательные поля.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(username=username).first():
            flash("Такой логин уже существует.", "danger")
            return render_template("auth/register.html")

        user = User(username=username, email=email, first_name=first_name,
                    last_name=last_name, role="student")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Регистрация выполнена. Теперь войдите.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")

@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.index"))
