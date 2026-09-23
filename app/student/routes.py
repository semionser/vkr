from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from app.models import Test, Attempt, StudentAnswer, Answer, TestGrade


student_bp = Blueprint("student", __name__)


def student_required():
    return current_user.role == "student"


def get_grade(test, percentage):
    grade = TestGrade.query.filter(
        TestGrade.test_id == test.id,
        TestGrade.min_percent <= percentage
    ).order_by(TestGrade.min_percent.desc()).first()

    return grade.grade if grade else 2


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


def finish_attempt(attempt, form):
    test = attempt.test

    StudentAnswer.query.filter_by(
        attempt_id=attempt.id
    ).delete(synchronize_session=False)

    score = 0

    questions = sorted(
        test.questions,
        key=lambda question: question.question_order
    )

    for question in questions:
        correct_answers = {
            answer.id
            for answer in question.answers
            if answer.is_correct
        }

        selected_answers = set()

        values = form.getlist(
            f"question_{question.id}"
        )

        for value in values:
            if not value.isdigit():
                continue

            answer = db.session.get(
                Answer,
                int(value)
            )

            if answer and answer.question_id == question.id:
                selected_answers.add(answer.id)

        question_correct = (
            len(correct_answers) > 0
            and selected_answers == correct_answers
        )

        question_points = question.points if question_correct else 0

        if question_correct:
            score += question.points

        if selected_answers:
            first_answer = True

            for answer_id in selected_answers:
                db.session.add(
                    StudentAnswer(
                        attempt_id=attempt.id,
                        question_id=question.id,
                        answer_id=answer_id,
                        is_correct=question_correct,
                        points=question_points if first_answer else 0
                    )
                )

                first_answer = False
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

    attempt.score = score

    if attempt.max_score:
        attempt.percentage = round(
            (score / attempt.max_score) * 100,
            2
        )
    else:
        attempt.percentage = 0

    attempt.grade = get_grade(
        test,
        attempt.percentage
    )

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

    attempts = Attempt.query.filter_by(
        student_id=current_user.id,
        status="completed"
    ).order_by(
        Attempt.completed_at.desc()
    ).limit(10).all()

    return render_template(
        "student/dashboard.html",
        disciplines=list(disciplines.values()),
        attempts=attempts
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

    if test.status != "published":
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

    max_score = sum(
        question.points
        for question in test.questions
    )

    attempt = Attempt(
        test_id=test.id,
        student_id=current_user.id,
        max_score=max_score,
        score=0,
        percentage=0,
        grade=None,
        status="in_progress",
        is_best=False
    )

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

    if elapsed_seconds >= time_limit_seconds:
        return finish_attempt(
            attempt,
            request.form
        )

    if request.method == "POST":
        return finish_attempt(
            attempt,
            request.form
        )

    remaining_seconds = max(
        0,
        int(
            time_limit_seconds - elapsed_seconds
        )
    )

    questions = sorted(
        attempt.test.questions,
        key=lambda question: question.question_order
    )

    return render_template(
        "student/take_test.html",
        attempt=attempt,
        questions=questions,
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

    return render_template(
        "student/result.html",
        attempt=attempt,
        attempts_count=attempts_count
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