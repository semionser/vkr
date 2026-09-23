"""
Логика прохождения теста, не зависящая от Flask-маршрутов:

* формирование набора вопросов попытки (случайная выборка и перемешивание);
* подсчёт баллов за вопрос (строгий и частичный режимы);
* правила показа разбора ошибок.

Вынесено в отдельный модуль, чтобы логику было удобно покрыть тестами.
"""

import json
import random

from app.models import Question


SCORING_MODES = {
    "strict": "Всё или ничего",
    "partial": "Частичные баллы",
}

REVIEW_MODES = {
    "none": "Не показывать",
    "own": "Только свои ответы (верно / неверно)",
    "after_all": "Правильные ответы — после последней попытки",
    "always": "Правильные ответы — сразу после попытки",
}


# =========================================================
# СОСТАВ ПОПЫТКИ
# =========================================================

def build_attempt_layout(test, rng=None):
    """
    Выбирает вопросы для новой попытки и порядок вариантов ответа.

    Возвращает (question_ids, answer_orders), где
    question_ids  — список id вопросов в порядке показа,
    answer_orders — {question_id: [answer_id, ...]}.
    """
    rng = rng or random.SystemRandom()

    questions = sorted(test.questions, key=lambda q: q.question_order)

    limit = test.questions_per_attempt
    if limit and 0 < limit < len(questions):
        # Случайная выборка из банка вопросов
        questions = rng.sample(questions, limit)
        if not test.shuffle_questions:
            # Сохраняем исходный порядок выбранных вопросов
            questions.sort(key=lambda q: q.question_order)

    if test.shuffle_questions:
        rng.shuffle(questions)

    answer_orders = {}
    for question in questions:
        answers = sorted(question.answers, key=lambda a: a.answer_order)
        ids = [a.id for a in answers]
        if test.shuffle_answers:
            rng.shuffle(ids)
        answer_orders[question.id] = ids

    return [q.id for q in questions], answer_orders


def apply_layout(attempt, question_ids, answer_orders):
    attempt.question_order_json = json.dumps(question_ids)
    attempt.answer_order_json = json.dumps(
        {str(k): v for k, v in answer_orders.items()}
    )


def attempt_questions(attempt):
    """
    Вопросы попытки в порядке показа: список (question, [answers]).

    Для старых попыток (до появления выборки) — все вопросы теста
    в исходном порядке. Вопросы, удалённые преподавателем, пропускаются.
    """
    test = attempt.test
    ids = attempt.question_ids

    if ids is None:
        questions = sorted(test.questions, key=lambda q: q.question_order)
    else:
        by_id = {q.id: q for q in test.questions}
        questions = [by_id[qid] for qid in ids if qid in by_id]

    orders = attempt.answer_orders
    result = []

    for question in questions:
        answers = sorted(question.answers, key=lambda a: a.answer_order)
        order = orders.get(question.id)
        if order:
            position = {aid: i for i, aid in enumerate(order)}
            # Новые варианты (добавленные после старта) — в конец
            answers.sort(key=lambda a: position.get(a.id, len(position)))
        result.append((question, answers))

    return result


def max_score_for(question_ids):
    if not question_ids:
        return 0
    questions = Question.query.filter(Question.id.in_(question_ids)).all()
    return sum(q.points for q in questions)


# =========================================================
# ПОДСЧЁТ БАЛЛОВ
# =========================================================

def score_question(question, selected_ids, mode="strict"):
    """
    Возвращает (баллы, полностью_верно).

    strict:  полный балл только если выбраны ровно все правильные варианты.
    partial: доля = (верно отмеченные − ошибочно отмеченные) / всего верных,
             ограниченная диапазоном [0; 1]. Штраф за лишние отметки не даёт
             получить балл, просто отметив все варианты.
    """
    correct = {a.id for a in question.answers if a.is_correct}
    selected = set(selected_ids)

    fully_correct = bool(correct) and selected == correct

    if fully_correct:
        return float(question.points), True

    if mode != "partial" or not correct or not selected:
        return 0.0, False

    hits = len(selected & correct)
    misses = len(selected - correct)
    ratio = max(0.0, (hits - misses) / len(correct))

    return round(question.points * ratio, 2), False


def grade_for(test, percentage):
    """Оценка по шкале теста (самый высокий порог, не превышающий процент)."""
    suitable = [g for g in test.grades if g.min_percent <= percentage]
    if not suitable:
        return 2
    return max(suitable, key=lambda g: g.min_percent).grade


# =========================================================
# РАЗБОР ОШИБОК
# =========================================================

def attempts_exhausted(test, attempts_count):
    return test.max_attempts is not None and attempts_count >= test.max_attempts


def review_permissions(attempt, attempts_count):
    """
    Что студенту можно увидеть после завершения попытки.

    Возвращает (показывать_разбор, показывать_правильные_ответы).
    """
    if attempt.status != "completed":
        return False, False

    mode = attempt.test.review_mode or "after_all"

    if mode == "none":
        return False, False
    if mode == "own":
        return True, False
    if mode == "always":
        return True, True

    # after_all: правильные ответы — только когда попыток больше не осталось
    return True, attempts_exhausted(attempt.test, attempts_count)
