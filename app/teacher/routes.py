from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required, current_user

from app import db

from app.models import (
    Test,
    Subject,
    Question,
    Answer,
    Attempt,
    TestGrade,
    Group,
    User
)
from app.quiz import SCORING_MODES, REVIEW_MODES


teacher_bp = Blueprint("teacher", __name__)


def teacher_required():
    return current_user.role == "teacher"


def options_context():
    """Данные для блока дополнительных параметров теста."""
    return {
        "groups": Group.query.order_by(Group.name).all(),
        "scoring_modes": SCORING_MODES,
        "review_modes": REVIEW_MODES,
    }


def apply_test_options(test, form):
    """
    Сохраняет перемешивание, выборку вопросов, режим оценивания,
    разбор ошибок и группы. Бросает ValueError при неверном числе.
    """
    test.shuffle_questions = form.get("shuffle_questions") == "1"
    test.shuffle_answers = form.get("shuffle_answers") == "1"

    raw_limit = form.get("questions_per_attempt", "").strip()
    test.questions_per_attempt = max(1, int(raw_limit)) if raw_limit else None

    scoring_mode = form.get("scoring_mode", "strict")
    test.scoring_mode = scoring_mode if scoring_mode in SCORING_MODES else "strict"

    review_mode = form.get("review_mode", "after_all")
    test.review_mode = review_mode if review_mode in REVIEW_MODES else "after_all"

    group_ids = {
        int(value)
        for value in form.getlist("group_ids")
        if value.isdigit()
    }

    test.groups = (
        Group.query.filter(Group.id.in_(group_ids)).all()
        if group_ids else []
    )



@teacher_bp.route("/dashboard")
@login_required
def dashboard():
    if not teacher_required():
        return redirect(url_for("main.index"))

    tests = (
        Test.query
        .filter_by(teacher_id=current_user.id)
        .order_by(Test.created_at.desc())
        .all()
    )

    subjects = Subject.query.order_by(Subject.name).all()

    return render_template(
        "teacher/dashboard.html",
        tests=tests,
        subjects=subjects,
    )

@teacher_bp.route("/test/<int:test_id>/status", methods=["POST"])
@login_required
def change_test_status(test_id):
    if not teacher_required():
        return redirect(url_for("main.index"))

    test = db.get_or_404(Test, test_id)

    if test.teacher_id != current_user.id:
        return redirect(url_for("teacher.dashboard"))

    new_status = request.form.get("status")

    if new_status == "published":
        if not test.questions:
            flash("Нельзя опубликовать тест без вопросов.", "danger")
            return redirect(url_for("teacher.dashboard"))

        test.status = "published"
        flash("Тест опубликован.", "success")

    elif new_status == "draft":
        test.status = "draft"
        flash("Тест снят с публикации.", "success")

    else:
        flash("Недопустимый статус.", "danger")

    db.session.commit()

    return redirect(url_for("teacher.dashboard"))


@teacher_bp.route(
    "/test/create",
    methods=["GET", "POST"]
)
@login_required
def create_test():

    if not teacher_required():
        return redirect(url_for("main.index"))

    subjects = (
        Subject.query
        .order_by(Subject.name)
        .all()
    )

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        subject_id = request.form.get(
            "subject_id"
        )

        if not title or not subject_id:

            flash(
                "Название и дисциплина обязательны.",
                "danger"
            )

            return render_template(
                "teacher/create_test.html",
                subjects=subjects,
                **options_context()
            )

        try:

            time_limit = max(
                1,
                int(
                    request.form.get(
                        "time_limit",
                        20
                    )
                )
            )

            passing_score = max(
                0,
                min(
                    100,
                    int(
                        request.form.get(
                            "passing_score",
                            60
                        )
                    )
                )
            )

            # Пустое поле = бесконечное количество попыток
            max_attempts_raw = request.form.get(
                "max_attempts",
                ""
            ).strip()

            if max_attempts_raw:
                max_attempts = max(
                    1,
                    int(max_attempts_raw)
                )
            else:
                max_attempts = None

            grade_5 = max(
                0,
                min(
                    100,
                    int(
                        request.form.get(
                            "grade_5",
                            90
                        )
                    )
                )
            )

            grade_4 = max(
                0,
                min(
                    100,
                    int(
                        request.form.get(
                            "grade_4",
                            75
                        )
                    )
                )
            )

            grade_3 = max(
                0,
                min(
                    100,
                    int(
                        request.form.get(
                            "grade_3",
                            60
                        )
                    )
                )
            )

            grade_2 = max(
                0,
                min(
                    100,
                    int(
                        request.form.get(
                            "grade_2",
                            0
                        )
                    )
                )
            )

        except (ValueError, TypeError):

            flash(
                "Проверьте числовые значения.",
                "danger"
            )

            return render_template(
                "teacher/create_test.html",
                subjects=subjects,
                **options_context()
            )

        # Создаём тест

        test = Test(
            title=title,
            description=description,
            subject_id=int(subject_id),
            teacher_id=current_user.id,
            time_limit=time_limit,
            passing_score=passing_score,
            max_attempts=max_attempts
        )

        try:
            apply_test_options(test, request.form)
        except (ValueError, TypeError):
            flash(
                "Проверьте количество вопросов в попытке.",
                "danger"
            )

            return render_template(
                "teacher/create_test.html",
                subjects=subjects,
                **options_context()
            )

        db.session.add(test)
        db.session.flush()

        # Создаём шкалу оценок

        grades = [
            (grade_5, 5),
            (grade_4, 4),
            (grade_3, 3),
            (grade_2, 2)
        ]

        for min_percent, grade in grades:

            db.session.add(
                TestGrade(
                    test_id=test.id,
                    min_percent=min_percent,
                    grade=grade
                )
            )

        db.session.commit()

        flash(
            "Тест создан.",
            "success"
        )

        return redirect(
            url_for(
                "teacher.edit_test",
                test_id=test.id
            )
        )

    return render_template(
        "teacher/create_test.html",
        subjects=subjects,
        **options_context()
    )


@teacher_bp.route(
    "/test/<int:test_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_test(test_id):

    if not teacher_required():
        return redirect(url_for("main.index"))

    test = db.get_or_404(
        Test,
        test_id
    )

    if test.teacher_id != current_user.id:

        return redirect(
            url_for("teacher.dashboard")
        )

    if request.method == "POST":

        question_text = request.form.get(
            "question_text",
            ""
        ).strip()

        try:

            points = max(
                1,
                int(
                    request.form.get(
                        "points",
                        1
                    )
                )
            )

        except (ValueError, TypeError):

            points = 1

        # Получаем все варианты
        option_texts = request.form.getlist(
            "option_text"
        )

        # Получаем все отмеченные правильные ответы
        correct_indexes = set(
            request.form.getlist(
                "correct"
            )
        )

        # Проверяем варианты

        options = []

        for index, text in enumerate(option_texts):

            text = text.strip()

            if text:

                options.append(
                    (
                        index,
                        text
                    )
                )

        # Проверки

        if not question_text:

            flash(
                "Введите текст вопроса.",
                "danger"
            )

        elif len(options) < 2:

            flash(
                "Добавьте минимум два варианта ответа.",
                "danger"
            )

        else:

            # Проверяем правильные ответы

            correct_options = [
                index
                for index, text in options
                if str(index) in correct_indexes
            ]

            if not correct_options:

                flash(
                    "Выберите хотя бы один правильный ответ.",
                    "danger"
                )

            else:

                # Создаём вопрос

                q = Question(
                    test_id=test.id,
                    text=question_text,
                    points=points,
                    question_order=len(
                        test.questions
                    ) + 1
                )

                db.session.add(q)
                db.session.flush()

                # Создаём ответы

                for answer_order, (
                    original_index,
                    text
                ) in enumerate(
                    options,
                    start=1
                ):

                    answer = Answer(
                        question_id=q.id,
                        text=text,
                        is_correct=(
                            str(original_index)
                            in correct_indexes
                        ),
                        answer_order=answer_order
                    )

                    db.session.add(answer)

                db.session.commit()

                flash(
                    "Вопрос добавлен.",
                    "success"
                )

                return redirect(
                    url_for(
                        "teacher.edit_test",
                        test_id=test.id
                    )
                )

    return render_template(
        "teacher/edit_test.html",
        test=test,
        **options_context()
    )


@teacher_bp.route("/test/<int:test_id>/settings", methods=["POST"])
@login_required
def update_test_settings(test_id):
    if not teacher_required():
        return redirect(url_for("main.index"))

    test = db.get_or_404(Test, test_id)

    if test.teacher_id != current_user.id:
        return redirect(url_for("teacher.dashboard"))

    title = request.form.get("title", "").strip()

    if not title:
        flash("Название теста не может быть пустым.", "danger")
        return redirect(url_for("teacher.edit_test", test_id=test.id))

    try:
        time_limit = max(1, int(request.form.get("time_limit", test.time_limit)))

        raw_attempts = request.form.get("max_attempts", "").strip()
        max_attempts = max(1, int(raw_attempts)) if raw_attempts else None

        apply_test_options(test, request.form)
    except (ValueError, TypeError):
        db.session.rollback()
        flash("Проверьте числовые значения.", "danger")
        return redirect(url_for("teacher.edit_test", test_id=test.id))

    test.title = title
    test.description = request.form.get("description", "").strip()
    test.time_limit = time_limit
    test.max_attempts = max_attempts

    db.session.commit()

    flash("Настройки теста сохранены.", "success")
    return redirect(url_for("teacher.edit_test", test_id=test.id))


@teacher_bp.route("/test/<int:test_id>/question/<int:question_id>/edit", methods=["GET", "POST"])
@login_required
def edit_question(test_id, question_id):
    if not teacher_required():
        return redirect(url_for("main.index"))

    test = db.get_or_404(Test, test_id)
    question = db.get_or_404(Question, question_id)

    if test.teacher_id != current_user.id or question.test_id != test.id:
        return redirect(url_for("teacher.dashboard"))

    if request.method == "POST":
        question_text = request.form.get("question_text", "").strip()

        try:
            points = max(1, int(request.form.get("points", 1)))
        except (ValueError, TypeError):
            points = 1

        option_texts = request.form.getlist("option_text")
        correct_indexes = set(request.form.getlist("correct"))

        options = []

        for index, text in enumerate(option_texts):
            text = text.strip()

            if text:
                options.append((index, text))

        if not question_text:
            flash("Введите текст вопроса.", "danger")
            return render_template("teacher/edit_question.html", test=test, question=question)

        if len(options) < 2:
            flash("Добавьте минимум два варианта ответа.", "danger")
            return render_template("teacher/edit_question.html", test=test, question=question)

        correct_options = [
            index for index, text in options
            if str(index) in correct_indexes
        ]

        if not correct_options:
            flash("Выберите хотя бы один правильный ответ.", "danger")
            return render_template("teacher/edit_question.html", test=test, question=question)

        question.text = question_text
        question.points = points

        for answer in question.answers:
            db.session.delete(answer)

        db.session.flush()

        for answer_order, (original_index, text) in enumerate(options, start=1):
            db.session.add(Answer(
                question_id=question.id,
                text=text,
                is_correct=str(original_index) in correct_indexes,
                answer_order=answer_order
            ))

        db.session.commit()

        flash("Вопрос изменён.", "success")
        return redirect(url_for("teacher.edit_test", test_id=test.id))

    return render_template("teacher/edit_question.html", test=test, question=question)


@teacher_bp.route("/test/<int:test_id>/question/<int:question_id>/delete", methods=["POST"])
@login_required
def delete_question(test_id, question_id):
    if not teacher_required():
        return redirect(url_for("main.index"))

    test = db.get_or_404(Test, test_id)
    question = db.get_or_404(Question, question_id)

    if test.teacher_id != current_user.id or question.test_id != test.id:
        return redirect(url_for("teacher.dashboard"))

    db.session.delete(question)
    db.session.commit()

    questions = Question.query.filter_by(test_id=test.id).order_by(Question.question_order).all()

    for index, item in enumerate(questions, start=1):
        item.question_order = index

    db.session.commit()

    flash("Вопрос удалён.", "success")
    return redirect(url_for("teacher.edit_test", test_id=test.id))


@teacher_bp.route(
    "/test/<int:test_id>/publish",
    methods=["POST"]
)
@login_required
def publish_test(test_id):

    test = db.get_or_404(
        Test,
        test_id
    )

    if not teacher_required():

        return redirect(
            url_for("main.index")
        )

    if test.teacher_id != current_user.id:

        return redirect(
            url_for("teacher.dashboard")
        )

    if not test.questions:

        flash(
            "Нельзя опубликовать тест без вопросов.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher.edit_test",
                test_id=test.id
            )
        )

    test.status = "published"

    db.session.commit()

    flash(
        "Тест опубликован.",
        "success"
    )

    return redirect(
        url_for("teacher.dashboard")
    )



@teacher_bp.route(
    "/test/<int:test_id>/delete",
    methods=["POST"]
)
@login_required
def delete_test(test_id):

    test = db.get_or_404(
        Test,
        test_id
    )

    if not teacher_required():

        return redirect(
            url_for("main.index")
        )

    if test.teacher_id != current_user.id:

        return redirect(
            url_for("teacher.dashboard")
        )

    db.session.delete(test)
    db.session.commit()

    flash(
        "Тест удалён.",
        "success"
    )

    return redirect(
        url_for("teacher.dashboard")
    )


@teacher_bp.route("/results")
@login_required
def results():

    if not teacher_required():
        return redirect(url_for("main.index"))

    query = (
        Attempt.query
        .join(Test)
        .filter(
            Test.teacher_id == current_user.id,
            Attempt.status == "completed"
        )
    )

    # Фильтр по учебной группе студента
    group_id = request.args.get("group", type=int)
    if group_id:
        query = (
            query
            .join(User, Attempt.student_id == User.id)
            .filter(User.group_id == group_id)
        )

    attempts = query.order_by(
        Attempt.completed_at.desc()
    ).all()

    return render_template(
        "teacher/results.html",
        attempts=attempts,
        groups=Group.query.order_by(Group.name).all(),
        current_group=group_id
    )
# =========================================================
# SUBJECTS — CREATE / EDIT / DELETE (для преподавателя)
# =========================================================

@teacher_bp.route("/subject/create", methods=["POST"])
@login_required
def create_subject():
    if not teacher_required():
        return redirect(url_for("main.index"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Название дисциплины не может быть пустым.", "danger")
        return redirect(url_for("teacher.dashboard"))

    existing = Subject.query.filter_by(name=name).first()
    if existing:
        flash(f"Дисциплина «{name}» уже существует.", "danger")
        return redirect(url_for("teacher.dashboard"))

    try:
        db.session.add(Subject(name=name, description=description))
        db.session.commit()
        flash(f"Дисциплина «{name}» добавлена.", "success")
    except Exception as e:
        db.session.rollback()
        print("CREATE SUBJECT ERROR:", e)
        flash(f"Не удалось добавить дисциплину: {e}", "danger")

    return redirect(url_for("teacher.dashboard"))


@teacher_bp.route("/subject/<int:subject_id>/edit", methods=["POST"])
@login_required
def edit_subject(subject_id):
    if not teacher_required():
        return redirect(url_for("main.index"))

    subject = db.get_or_404(Subject, subject_id)

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Название дисциплины не может быть пустым.", "danger")
        return redirect(url_for("teacher.dashboard"))

    # Проверяем, что новое имя не занято другой дисциплиной
    duplicate = Subject.query.filter(
        Subject.name == name,
        Subject.id != subject.id,
    ).first()

    if duplicate:
        flash(f"Дисциплина «{name}» уже существует.", "danger")
        return redirect(url_for("teacher.dashboard"))

    try:
        subject.name = name
        subject.description = description
        db.session.commit()
        flash(f"Дисциплина «{name}» обновлена.", "success")
    except Exception as e:
        db.session.rollback()
        print("EDIT SUBJECT ERROR:", e)
        flash(f"Не удалось изменить дисциплину: {e}", "danger")

    return redirect(url_for("teacher.dashboard"))


@teacher_bp.route("/subject/<int:subject_id>/delete", methods=["POST"])
@login_required
def delete_subject(subject_id):
    if not teacher_required():
        return redirect(url_for("main.index"))

    subject = db.get_or_404(Subject, subject_id)

    # Преподаватель может удалить дисциплину, только если у него есть
    # хотя бы один тест в ней (иначе — чужая дисциплина).
    own_test = Test.query.filter_by(
        subject_id=subject.id,
        teacher_id=current_user.id,
    ).first()

    if not own_test:
        flash("Нельзя удалить дисциплину, в которой нет ваших тестов.", "warning")
        return redirect(url_for("teacher.dashboard"))

    subject_name = subject.name

    try:
        db.session.delete(subject)
        db.session.commit()
        flash(f"Дисциплина «{subject_name}» удалена.", "success")
    except Exception as e:
        db.session.rollback()
        print("DELETE SUBJECT ERROR:", e)
        flash(f"Не удалось удалить дисциплину: {e}", "danger")

    return redirect(url_for("teacher.dashboard"))
