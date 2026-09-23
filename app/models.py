import json
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


# =========================================================
# TEST ↔ GROUP (многие ко многим)
# Если у теста нет ни одной группы — он доступен всем студентам.
# =========================================================

test_groups = db.Table(
    "test_groups",
    db.Column(
        "test_id",
        db.Integer,
        db.ForeignKey("tests.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "group_id",
        db.Integer,
        db.ForeignKey("groups.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# =========================================================
# GROUP (учебная группа)
# =========================================================

class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    students = db.relationship(
        "User",
        back_populates="group",
        lazy=True,
    )


# =========================================================
# USER
# =========================================================

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    role = db.Column(db.String(20), nullable=False, default="student")
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Учебная группа (только для студентов)
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True,
    )

    group = db.relationship("Group", back_populates="students")

    # Тесты, созданные пользователем, удаляются вместе с ним
    created_tests = db.relationship(
        "Test",
        foreign_keys="Test.teacher_id",
        backref="teacher",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Попытки пользователя удаляются вместе с ним
    attempts = db.relationship(
        "Attempt",
        foreign_keys="Attempt.student_id",
        backref="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_user


# =========================================================
# SUBJECT
# =========================================================

class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text)

    tests = db.relationship(
        "Test",
        backref="subject",
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# =========================================================
# TEST
# =========================================================

class Test(db.Model):
    __tablename__ = "tests"

    id = db.Column(db.Integer, primary_key=True)

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    time_limit = db.Column(db.Integer, nullable=False, default=20)
    passing_score = db.Column(db.Integer, nullable=False, default=60)
    max_attempts = db.Column(db.Integer, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="draft")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Защита от списывания ---
    shuffle_questions = db.Column(db.Boolean, nullable=False, default=False)
    shuffle_answers = db.Column(db.Boolean, nullable=False, default=False)
    # Сколько вопросов случайно выбирать из банка; None = все вопросы
    questions_per_attempt = db.Column(db.Integer, nullable=True)

    # --- Оценивание ---
    # "strict"  — балл только за полностью верный ответ
    # "partial" — частичный балл за вопросы с несколькими ответами
    scoring_mode = db.Column(db.String(20), nullable=False, default="strict")

    # --- Разбор ошибок после завершения ---
    # "none"      — только итог
    # "own"       — свои ответы и отметки верно/неверно
    # "after_all" — как "own", а правильные ответы после последней попытки
    # "always"    — правильные ответы сразу после каждой попытки
    review_mode = db.Column(db.String(20), nullable=False, default="after_all")

    groups = db.relationship(
        "Group",
        secondary=test_groups,
        lazy="subquery",
        backref=db.backref("tests", lazy=True),
    )

    def is_available_for(self, user):
        """Доступен ли тест студенту с учётом учебных групп."""
        if not self.groups:
            return True
        return user.group_id is not None and any(
            g.id == user.group_id for g in self.groups
        )

    questions = db.relationship(
        "Question",
        backref="test",
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    grades = db.relationship(
        "TestGrade",
        backref="test",
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    attempts = db.relationship(
        "Attempt",
        back_populates="test",
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# =========================================================
# QUESTION
# =========================================================

class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)

    test_id = db.Column(
        db.Integer,
        db.ForeignKey("tests.id", ondelete="CASCADE"),
        nullable=False,
    )

    text = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, nullable=False, default=1)
    question_order = db.Column(db.Integer, nullable=False, default=1)

    answers = db.relationship(
        "Answer",
        backref="question",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Answer.answer_order",
        passive_deletes=True,
    )

    student_answers = db.relationship(
        "StudentAnswer",
        backref="question",
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# =========================================================
# ANSWER
# =========================================================

class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )

    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    answer_order = db.Column(db.Integer, nullable=False, default=1)

    student_answers = db.relationship(
        "StudentAnswer",
        backref="answer",
        lazy=True,
        passive_deletes=True,
    )


# =========================================================
# TEST GRADE
# =========================================================

class TestGrade(db.Model):
    __tablename__ = "test_grades"

    id = db.Column(db.Integer, primary_key=True)

    test_id = db.Column(
        db.Integer,
        db.ForeignKey("tests.id", ondelete="CASCADE"),
        nullable=False,
    )

    min_percent = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.Integer, nullable=False)


# =========================================================
# ATTEMPT
# =========================================================

class Attempt(db.Model):
    __tablename__ = "attempts"

    __table_args__ = (
        db.Index("ix_attempt_student_test", "student_id", "test_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    test_id = db.Column(
        db.Integer,
        db.ForeignKey("tests.id", ondelete="CASCADE"),
        nullable=False,
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    started_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    completed_at = db.Column(db.DateTime)

    # Float — при частичном оценивании балл может быть дробным
    score = db.Column(db.Float, default=0, nullable=False)
    max_score = db.Column(db.Integer, default=0, nullable=False)
    percentage = db.Column(db.Float, default=0, nullable=False)
    grade = db.Column(db.Integer)

    status = db.Column(
        db.String(20),
        default="in_progress",
        nullable=False,
    )

    is_best = db.Column(db.Boolean, default=False, nullable=False)

    # Набор вопросов этой попытки и порядок вариантов (JSON).
    # Фиксируется при старте, чтобы обновление страницы
    # не меняло вопросы и порядок ответов.
    question_order_json = db.Column(db.Text)  # [qid, qid, ...]
    answer_order_json = db.Column(db.Text)    # {"qid": [aid, aid, ...]}

    @property
    def question_ids(self):
        """ID вопросов попытки в порядке показа (или None для старых попыток)."""
        if not self.question_order_json:
            return None
        return json.loads(self.question_order_json)

    @property
    def answer_orders(self):
        if not self.answer_order_json:
            return {}
        return {int(k): v for k, v in json.loads(self.answer_order_json).items()}

    test = db.relationship(
        "Test",
        back_populates="attempts",
    )

    student_answers = db.relationship(
        "StudentAnswer",
        backref="attempt",
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# =========================================================
# STUDENT ANSWER
# =========================================================

class StudentAnswer(db.Model):
    __tablename__ = "student_answers"

    id = db.Column(db.Integer, primary_key=True)

    attempt_id = db.Column(
        db.Integer,
        db.ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )

    answer_id = db.Column(
        db.Integer,
        db.ForeignKey("answers.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    points = db.Column(db.Float, default=0, nullable=False)