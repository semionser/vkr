from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from sqlalchemy import func, desc

from app import db
from app.models import User, Subject, Test, Attempt, Group



admin_bp = Blueprint("admin", __name__)


def admin_required():
    return current_user.is_authenticated and current_user.role == "admin"


# =========================================================
# DASHBOARD
# =========================================================
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if not admin_required():
        return redirect(url_for("main.index"))

    users = User.query.order_by(User.created_at.desc()).all()
    subjects = Subject.query.order_by(Subject.name).all()
    groups = Group.query.order_by(Group.name).all()

    # =========================================================
    # АНАЛИТИКА
    # =========================================================

    # Успеваемость считается только по ЛУЧШЕЙ попытке студента
    # в каждом тесте: неудачные пробные попытки не портят статистику.
    # Активность (попытки за неделю/месяц, лента) — по всем попыткам.
    best_only = (Attempt.status == "completed", Attempt.is_best.is_(True))

    # 1. Распределение оценок (2, 3, 4, 5)
    grade_rows = (
        db.session.query(Attempt.grade, func.count(Attempt.id))
        .filter(*best_only, Attempt.grade.isnot(None))
        .group_by(Attempt.grade)
        .all()
    )

    grade_distribution = {2: 0, 3: 0, 4: 0, 5: 0}
    for grade, count in grade_rows:
        if grade in grade_distribution:
            grade_distribution[grade] = count

    total_completed = sum(grade_distribution.values())

    # 2. Средний процент по лучшим результатам
    avg_row = (
        db.session.query(func.avg(Attempt.percentage))
        .filter(*best_only)
        .scalar()
    )
    avg_percentage = round(float(avg_row or 0), 1)

    # 3. Количество попыток за 7 и 30 дней
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    attempts_week = (
        Attempt.query
        .filter(
            Attempt.status == "completed",
            Attempt.completed_at >= week_ago,
        )
        .count()
    )

    attempts_month = (
        Attempt.query
        .filter(
            Attempt.status == "completed",
            Attempt.completed_at >= month_ago,
        )
        .count()
    )

    # 4. Топ-5 студентов по среднему лучшему результату
    top_students_rows = (
        db.session.query(
            User,
            func.count(Attempt.id).label("cnt"),
            func.avg(Attempt.percentage).label("avg_pct"),
        )
        .join(Attempt, Attempt.student_id == User.id)
        .filter(*best_only)
        .group_by(User.id)
        .order_by(desc("avg_pct"), desc("cnt"))
        .limit(5)
        .all()
    )

    top_students = [
        {
            "user": user,
            "attempts": cnt,
            "avg_percentage": round(float(avg_pct or 0), 1),
        }
        for user, cnt, avg_pct in top_students_rows
    ]

    # 5. Статистика по дисциплинам — средний лучший результат и число сданных тестов
    subject_stats_rows = (
        db.session.query(
            Subject,
            func.count(Attempt.id).label("cnt"),
            func.avg(Attempt.percentage).label("avg_pct"),
        )
        .join(Test, Test.subject_id == Subject.id)
        .join(Attempt, Attempt.test_id == Test.id)
        .filter(*best_only)
        .group_by(Subject.id)
        .order_by(desc("cnt"))
        .all()
    )

    subject_stats = [
        {
            "subject": subject,
            "attempts": cnt,
            "avg_percentage": round(float(avg_pct or 0), 1),
        }
        for subject, cnt, avg_pct in subject_stats_rows
    ]

    # 6. Последние 6 попыток (для ленты активности)
    recent_attempts = (
        Attempt.query
        .filter(Attempt.status == "completed")
        .order_by(Attempt.completed_at.desc())
        .limit(6)
        .all()
    )

    # 7. Пользователи по ролям
    role_stats = {
        "students": User.query.filter_by(role="student").count(),
        "teachers": User.query.filter_by(role="teacher").count(),
        "admins":   User.query.filter_by(role="admin").count(),
    }

    return render_template(
        "admin/dashboard.html",
        users=users,
        subjects=subjects,
        groups=groups,
        # аналитика
        grade_distribution=grade_distribution,
        total_completed=total_completed,
        avg_percentage=avg_percentage,
        attempts_week=attempts_week,
        attempts_month=attempts_month,
        top_students=top_students,
        subject_stats=subject_stats,
        recent_attempts=recent_attempts,
        role_stats=role_stats,
    )


# =========================================================
# USERS — TOGGLE ACTIVE
# =========================================================

@admin_bp.route("/user/<int:user_id>/toggle", methods=["POST"])
@login_required
def toggle_user(user_id):
    if not admin_required():
        return redirect(url_for("main.index"))

    user = db.get_or_404(User, user_id)

    if user.id == current_user.id:
        flash("Нельзя изменить статус собственной учётной записи.", "warning")
        return redirect(url_for("admin.dashboard"))

    user.is_active_user = not user.is_active_user
    db.session.commit()

    flash(
        f"Пользователь {user.username}: "
        f"{'активирован' if user.is_active_user else 'заблокирован'}.",
        "success"
    )

    return redirect(url_for("admin.dashboard"))


# =========================================================
# USERS — CHANGE ROLE
# =========================================================

@admin_bp.route("/user/<int:user_id>/role", methods=["POST"])
@login_required
def change_user_role(user_id):
    if not admin_required():
        return redirect(url_for("main.index"))

    user = db.get_or_404(User, user_id)
    role = request.form.get("role", "").strip().lower()

    allowed_roles = {"student", "teacher", "admin"}

    if role not in allowed_roles:
        flash("Указана недопустимая роль.", "danger")
        return redirect(url_for("admin.dashboard"))

    if user.id == current_user.id and role != "admin":
        flash("Нельзя изменить собственную роль администратора.", "warning")
        return redirect(url_for("admin.dashboard"))

    if user.role == role:
        flash("Роль пользователя уже установлена.", "info")
        return redirect(url_for("admin.dashboard"))

    user.role = role
    db.session.commit()

    role_names = {
        "student": "Студент",
        "teacher": "Преподаватель",
        "admin":   "Администратор",
    }

    flash(
        f"Роль пользователя {user.username} изменена на "
        f"«{role_names[role]}».",
        "success"
    )

    return redirect(url_for("admin.dashboard"))


# =========================================================
# USERS — DELETE
# =========================================================

@admin_bp.route("/user/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_user(user_id):
    if not admin_required():
        return redirect(url_for("main.index"))

    user = db.get_or_404(User, user_id)

    if user.id == current_user.id:
        flash("Нельзя удалить собственную учётную запись.", "warning")
        return redirect(url_for("admin.dashboard"))

    username = user.username

    try:
        db.session.delete(user)
        db.session.commit()

        flash(f"Пользователь {username} удалён.", "success")
    except Exception as e:
        db.session.rollback()
        print("DELETE USER ERROR:", e)

        flash(
            f"Не удалось удалить пользователя {username}: {e}",
            "danger"
        )

    return redirect(url_for("admin.dashboard"))


# =========================================================
# SUBJECTS — CREATE
# =========================================================

@admin_bp.route("/subject/create", methods=["POST"])
@login_required
def create_subject():
    if not admin_required():
        return redirect(url_for("main.index"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Название дисциплины не может быть пустым.", "danger")
        return redirect(url_for("admin.dashboard"))

    existing = Subject.query.filter_by(name=name).first()

    if existing:
        flash(f"Дисциплина «{name}» уже существует.", "danger")
        return redirect(url_for("admin.dashboard"))

    try:
        db.session.add(Subject(name=name, description=description))
        db.session.commit()

        flash(f"Дисциплина «{name}» добавлена.", "success")
    except Exception as e:
        db.session.rollback()
        print("CREATE SUBJECT ERROR:", e)

        flash(f"Не удалось добавить дисциплину: {e}", "danger")

    return redirect(url_for("admin.dashboard"))


# =========================================================
# SUBJECTS — DELETE
# =========================================================

@admin_bp.route("/subject/<int:subject_id>/delete", methods=["POST"])
@login_required
def delete_subject(subject_id):
    if not admin_required():
        return redirect(url_for("main.index"))

    subject = db.get_or_404(Subject, subject_id)

    subject_name = subject.name

    try:
        db.session.delete(subject)
        db.session.commit()

        flash(f"Дисциплина «{subject_name}» удалена.", "success")
    except Exception as e:
        db.session.rollback()
        print("DELETE SUBJECT ERROR:", e)

        flash(
            f"Не удалось удалить дисциплину {subject_name}: {e}",
            "danger"
        )

    return redirect(url_for("admin.dashboard"))

# =========================================================
# TESTS — DELETE
# =========================================================

@admin_bp.route("/test/<int:test_id>/delete", methods=["POST"])
@login_required
def delete_test(test_id):
    if not admin_required():
        return redirect(url_for("main.index"))

    test = db.get_or_404(Test, test_id)

    test_title = test.title

    try:
        db.session.delete(test)
        db.session.commit()
        flash(f"Тест «{test_title}» удалён.", "success")
    except Exception as e:
        db.session.rollback()
        print("DELETE TEST ERROR:", e)
        flash(f"Не удалось удалить тест {test_title}: {e}", "danger")

    return redirect(url_for("admin.dashboard"))


# =========================================================
# GROUPS — CREATE / RENAME / DELETE
# =========================================================

@admin_bp.route("/group/create", methods=["POST"])
@login_required
def create_group():
    if not admin_required():
        return redirect(url_for("main.index"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip() or None

    if not name:
        flash("Название группы не может быть пустым.", "danger")
        return redirect(url_for("admin.dashboard") + "#groups")

    if Group.query.filter_by(name=name).first():
        flash(f"Группа «{name}» уже существует.", "danger")
        return redirect(url_for("admin.dashboard") + "#groups")

    db.session.add(Group(name=name, description=description))
    db.session.commit()

    flash(f"Группа «{name}» создана.", "success")
    return redirect(url_for("admin.dashboard") + "#groups")


@admin_bp.route("/group/<int:group_id>/edit", methods=["POST"])
@login_required
def edit_group(group_id):
    if not admin_required():
        return redirect(url_for("main.index"))

    group = db.get_or_404(Group, group_id)
    name = request.form.get("name", "").strip()

    if not name:
        flash("Название группы не может быть пустым.", "danger")
        return redirect(url_for("admin.dashboard") + "#groups")

    duplicate = Group.query.filter(Group.name == name, Group.id != group.id).first()
    if duplicate:
        flash(f"Группа «{name}» уже существует.", "danger")
        return redirect(url_for("admin.dashboard") + "#groups")

    group.name = name
    group.description = request.form.get("description", "").strip() or None
    db.session.commit()

    flash(f"Группа «{name}» обновлена.", "success")
    return redirect(url_for("admin.dashboard") + "#groups")


@admin_bp.route("/group/<int:group_id>/delete", methods=["POST"])
@login_required
def delete_group(group_id):
    if not admin_required():
        return redirect(url_for("main.index"))

    group = db.get_or_404(Group, group_id)
    name = group.name

    # Студенты остаются без группы, тесты теряют привязку к ней
    for student in group.students:
        student.group_id = None
    group.tests = []

    db.session.delete(group)
    db.session.commit()

    flash(f"Группа «{name}» удалена. Студенты из неё остались без группы.", "success")
    return redirect(url_for("admin.dashboard") + "#groups")


@admin_bp.route("/user/<int:user_id>/group", methods=["POST"])
@login_required
def change_user_group(user_id):
    if not admin_required():
        return redirect(url_for("main.index"))

    user = db.get_or_404(User, user_id)
    raw = request.form.get("group_id", "").strip()

    if raw:
        group = db.session.get(Group, int(raw)) if raw.isdigit() else None
        if group is None:
            flash("Группа не найдена.", "danger")
            return redirect(url_for("admin.dashboard"))
        user.group_id = group.id
        message = f"{user.username} переведён в группу «{group.name}»."
    else:
        user.group_id = None
        message = f"{user.username} исключён из группы."

    db.session.commit()
    flash(message, "success")
    return redirect(url_for("admin.dashboard"))
