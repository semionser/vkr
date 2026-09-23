from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == "student":
            return redirect(url_for("student.dashboard"))
        if current_user.role == "teacher":
            return redirect(url_for("teacher.dashboard"))
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
    return render_template("index.html")
