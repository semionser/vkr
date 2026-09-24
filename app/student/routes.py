from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from app.security import require_role
from app.models import Test, Attempt, StudentAnswer
from app.quiz import (
    apply_layout,
    attempt_questions,
    build_attempt_layout,
    grade_for,
    max_score_for,
    review_permissions,
    score_question,
)


student_bp = Blueprint("student", __name__)

# Все маршруты раздела — только для роли «student» (см. app/security.py)
require_role(student_bp, "student")


# Запас на задержку сети при автоотправке формы по таймеру.
# Ответы, пришедшие позже, не засчитываются.
TIME_GRACE_SECONDS = 30


def student_required():
    return current_user.role == "student"


def get_attempt_count(test_id, student_id):
    return Attempt.query.filter_by(
        test_id=test_id,
        student_id=student_id
    ).count()


def get_in_progress_attempt(test_id, student_id):
    return Attempt.query.filter_by(
        test_id=test_id,
        student_id=student_id,
        status="in_progress"
    ).first()


def get_best_attempt(test_id, student_id):
    return Attempt.query.filter_by(
        test_id=test_id,
        student_id=student_id,
        status="completed",
        is_best=True
    ).first()


def update_best_attempt(attempt):
    previous_best = get_best_attempt(
        attempt.test_id,
        attempt.student_id
    )

    if previous_best and previous_best.id != attempt.id:
        if previous_best.percentage >= attempt.percentage:
            attempt.is_best = False
            return

        previous_best.is_best = False

    attempt.is_best = True


def selected_answer_ids(form, question, answers):
    """ID вариантов, отмеченных студентом, только из этого вопроса."""
    if form is None:
        return set()

    allowed = {a.id for a in answers}
    selected = set()

    for value in form.getlist(f"question_{question.id}"):
        if value.isdigit() and int(value) in allowed:
            selected.add(int(value))

    return selected


def finish_attempt(attempt, form):
    """
    Проверяет ответы и завершает попытку.
    form=None — время вышло, ответы не принимаются.
    """
    test = attempt.test
    mode = test.scoring_mode or "strict"

    StudentAnswer.query.filter_by(
        attempt_id=attempt.id
    ).delete(synchronize_session=False)

    score = 0.0

    for question, answers in attempt_questions(attempt):
        selected = selected_answer_ids(form, question, answers)
        points, fully_correct = score_question(question, selected, mode)
        score += points

        if selected:
            # Баллы за вопрос записываются в первую строку,
            # чтобы сумма по StudentAnswer совпадала со score
            for index, answer_id in enumerate(sorted(selected)):
                db.session.add(
                    StudentAnswer(
                        attempt_id=attempt.id,
                        question_id=question.id,
                        answer_id=answer_id,
                        is_correct=fully_correct,
                        points=points if index == 0 else 0
                    )
                )
        else:
            db.session.add(
                StudentAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    answer_id=None,
                    is_correct=False,
                    points=0
                )
            )

    attempt.score = round(score, 2)

    if attempt.max_score:
        attempt.percentage = round(
            (score / attempt.max_score) * 100,
            2
        )
    else:
        attempt.percentage = 0

    attempt.grade = grade_for(test, attempt.percentage)

    attempt.completed_at = datetime.utcnow()
    attempt.status = "completed"

    update_best_attempt(attempt)

    db.session.commit()

    return redirect(
        url_for(
            "student.result",
            attempt_id=attempt.id
        )
    )


@student_bp.route("/dashboard")
@login_required
def dashboard():
    if not student_required():
        return redirect(url_for("main.index"))

    tests = Test.query.filter_by(
        status="published"
    ).order_by(
        Test.created_at.desc()
    ).all()

    disciplines = {}

    for test in tests:
        if not test.questions:
            continue

        # Тест назначен другим группам — студент его не видит
        if not test.is_available_for(current_user):
            continue

        attempts_count = get_attempt_count(
            test.id,
            current_user.id
        )

        best_attempt = get_best_attempt(
            test.id,
            current_user.id
        )

        in_progress_attempt = get_in_progress_attempt(
            test.id,
            current_user.id
        )

        if test.max_attempts is None:
            attempts_left = None
        else:
            attempts_left = max(
                0,
                test.max_attempts - attempts_count
            )

        if in_progress_attempt:
            sort_order = 0
        elif attempts_count == 0:
            sort_order = 1
        elif (
            test.max_attempts is None
            or attempts_left > 0
        ):
            sort_order = 2
        else:
            sort_order = 3

        subject = test.subject

        if subject.id not in disciplines:
            disciplines[subject.id] = {
                "subject": subject,
                "tests": []
            }

        disciplines[subject.id]["tests"].append({
            "test": test,
            "attempts_count": attempts_count,
            "attempts_left": attempts_left,
            "best_attempt": best_attempt,
            "in_progress_attempt": in_progress_attempt,
            "sort_order": sort_order
        })

    # Сортируем тесты внутри каждой дисциплины.
    # 0 — продолжить
    # 1 — ещё не проходился
    # 2 — остались попытки
    # 3 — завершён
    for item in disciplines.values():
        item["tests"].sort(
            key=lambda test_item: (
                test_item["sort_order"],
                test_item["test"].created_at
            )
        )

        passed = [t for t in item["tests"] if t["best_attempt"]]
        item["passed"] = len(passed)
        item["total"] = len(item["tests"])
        item["avg_percentage"] = (
            round(sum(t["best_attempt"].percentage for t in passed) / len(passed))
            if passed else None
        )

    all_items = [t for item in disciplines.values() for t in item["tests"]]

    # «Нужно пройти»: начатые и ещё не открытые тесты
    todo = sorted(
        (t for t in all_items if t["sort_order"] in (0, 1)),
        key=lambda t: (t["sort_order"], t["test"].created_at)
    )

    best = [t["best_attempt"] for t in all_items if t["best_attempt"]]
    stats = {
        "available": len(all_items),
        "passed": len(best),
        "avg_percentage": round(sum(a.percentage for a in best) / len(best)) if best else None,
        "avg_grade": (
            round(sum(a.grade or 2 for a in best) / len(best), 1) if best else None
        ),
    }

    # Лучшие результаты: лучшая попытка по каждому тесту, свежие сверху
    recent = Attempt.query.filter_by(
        student_id=current_user.id,
        status="completed",
        is_best=True
    ).order_by(Attempt.completed_at.desc()).limit(6).all()

    return render_template(
        "student/dashboard.html",
        disciplines=sorted(disciplines.values(), key=lambda d: d["subject"].name),
        todo=todo,
        stats=stats,
        attempts=recent
    )



@student_bp.route("/test/<int:test_id>/start")
@login_required
def start_test(test_id):
    if not student_required():
        return redirect(url_for("main.index"))

    test = db.get_or_404(
        Test,
        test_id
    )

    if test.status != "published" or not test.is_available_for(current_user):
        flash(
            "Тест недоступен.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )

    if not test.questions:
        flash(
            "В тесте нет вопросов.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )

    existing_attempt = get_in_progress_attempt(
        test.id,
        current_user.id
    )

    if existing_attempt:
        return redirect(
            url_for(
                "student.take_test",
                attempt_id=existing_attempt.id
            )
        )

    attempts_count = get_attempt_count(
        test.id,
        current_user.id
    )

    if (
        test.max_attempts is not None
        and attempts_count >= test.max_attempts
    ):
        flash(
            "Вы использовали все доступные попытки.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )

    # Случайная выборка вопросов и перемешивание фиксируются
    # в попытке, чтобы не меняться при обновлении страницы
    question_ids, answer_orders = build_attempt_layout(test)

    attempt = Attempt(
        test_id=test.id,
        student_id=current_user.id,
        max_score=max_score_for(question_ids),
        score=0,
        percentage=0,
        grade=None,
        status="in_progress",
        is_best=False
    )

    apply_layout(attempt, question_ids, answer_orders)

    db.session.add(attempt)
    db.session.commit()

    return redirect(
        url_for(
            "student.take_test",
            attempt_id=attempt.id
        )
    )


@student_bp.route(
    "/attempt/<int:attempt_id>",
    methods=["GET", "POST"]
)
@login_required
def take_test(attempt_id):
    if not student_required():
        return redirect(url_for("main.index"))

    attempt = db.get_or_404(
        Attempt,
        attempt_id
    )

    if attempt.student_id != current_user.id:
        return redirect(url_for("main.index"))

    if attempt.status != "in_progress":
        return redirect(
            url_for(
                "student.result",
                attempt_id=attempt.id
            )
        )

    now = datetime.utcnow()

    elapsed_seconds = (
        now - attempt.started_at
    ).total_seconds()

    time_limit_seconds = (
        attempt.test.time_limit * 60
    )

    if elapsed_seconds >= time_limit_seconds + TIME_GRACE_SECONDS:
        # Время вышло давно — ответы из формы не принимаем
        flash("Время на прохождение теста истекло.", "warning")
        return finish_attempt(attempt, None)

    if request.method == "POST":
        return finish_attempt(
            attempt,
            request.form
        )

    if elapsed_seconds >= time_limit_seconds:
        return finish_attempt(attempt, None)

    remaining_seconds = max(
        0,
        int(
            time_limit_seconds - elapsed_seconds
        )
    )

    return render_template(
        "student/take_test.html",
        attempt=attempt,
        items=attempt_questions(attempt),
        remaining_seconds=remaining_seconds
    )


@student_bp.route("/result/<int:attempt_id>")
@login_required
def result(attempt_id):
    if not student_required():
        return redirect(url_for("main.index"))

    attempt = db.get_or_404(
        Attempt,
        attempt_id
    )

    if attempt.student_id != current_user.id:
        return redirect(url_for("main.index"))

    attempts_count = get_attempt_count(
        attempt.test_id,
        current_user.id
    )

    can_review, _ = review_permissions(attempt, attempts_count)

    return render_template(
        "student/result.html",
        attempt=attempt,
        attempts_count=attempts_count,
        can_review=can_review
    )


@student_bp.route("/result/<int:attempt_id>/review")
@login_required
def review(attempt_id):
    if not student_required():
        return redirect(url_for("main.index"))

    attempt = db.get_or_404(Attempt, attempt_id)

    if attempt.student_id != current_user.id:
        return redirect(url_for("main.index"))

    attempts_count = get_attempt_count(attempt.test_id, current_user.id)
    can_review, show_correct = review_permissions(attempt, attempts_count)

    if not can_review:
        flash("Преподаватель отключил просмотр разбора для этого теста.", "warning")
        return redirect(url_for("student.result", attempt_id=attempt.id))

    # Ответы студента по вопросам
    chosen = {}
    earned = {}
    for sa in attempt.student_answers:
        if sa.answer_id is not None:
            chosen.setdefault(sa.question_id, set()).add(sa.answer_id)
        earned[sa.question_id] = earned.get(sa.question_id, 0) + (sa.points or 0)

    items = []
    for question, answers in attempt_questions(attempt):
        selected = chosen.get(question.id, set())
        points = earned.get(question.id, 0)

        if points >= question.points:
            status = "correct"
        elif points > 0:
            status = "partial"
        else:
            status = "wrong"

        items.append({
            "question": question,
            "answers": answers,
            "selected": selected,
            "points": points,
            "status": status,
        })

    summary = {
        "correct": sum(1 for i in items if i["status"] == "correct"),
        "partial": sum(1 for i in items if i["status"] == "partial"),
        "wrong": sum(1 for i in items if i["status"] == "wrong"),
    }

    attempts_left = None
    if attempt.test.max_attempts is not None:
        attempts_left = max(0, attempt.test.max_attempts - attempts_count)

    return render_template(
        "student/review.html",
        attempt=attempt,
        items=items,
        summary=summary,
        show_correct=show_correct,
        attempts_left=attempts_left
    )


@student_bp.route("/history")
@login_required
def history():
    if not student_required():
        return redirect(url_for("main.index"))

    attempts = Attempt.query.filter_by(
        student_id=current_user.id,
        status="completed"
    ).order_by(
        Attempt.completed_at.desc()
    ).all()

    return render_template(
        "student/history.html",
        attempts=attempts
    )
