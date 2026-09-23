"""
Автотесты новой логики: выборка и перемешивание вопросов,
частичное оценивание, разбор ошибок, учебные группы.

Запуск из корня проекта:
    python -m unittest discover tests -v
(или просто `pytest`, если он установлен)
"""

import random
import re
import unittest
from datetime import timedelta
from types import SimpleNamespace

from app import create_app, db
from app.models import (
    Answer,
    Attempt,
    Group,
    Question,
    Subject,
    Test,
    TestGrade,
    User,
)
from app.quiz import build_attempt_layout, review_permissions, score_question


# =========================================================
# Вспомогательные функции
# =========================================================

def make_question(test, text, points, answers, order):
    """answers: список (текст, правильный?)"""
    q = Question(test_id=test.id, text=text, points=points, question_order=order)
    db.session.add(q)
    db.session.flush()
    for i, (a_text, ok) in enumerate(answers, start=1):
        db.session.add(Answer(question_id=q.id, text=a_text, is_correct=ok, answer_order=i))
    db.session.flush()
    return q


class BaseCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.g1 = Group(name="ИВТ-21")
        self.g2 = Group(name="ПИ-22")
        db.session.add_all([self.g1, self.g2])
        db.session.flush()

        self.teacher = self.make_user("teacher", "teacher")
        self.s1 = self.make_user("s1", "student", self.g1)
        self.s2 = self.make_user("s2", "student", self.g2)
        self.s_nogroup = self.make_user("s3", "student")

        self.subject = Subject(name="Программирование")
        db.session.add(self.subject)
        db.session.flush()

        self.test = Test(
            subject_id=self.subject.id,
            teacher_id=self.teacher.id,
            title="Демо",
            time_limit=10,
            max_attempts=2,
            status="published",
        )
        db.session.add(self.test)
        db.session.flush()

        for min_percent, grade in [(90, 5), (75, 4), (60, 3), (0, 2)]:
            db.session.add(TestGrade(test_id=self.test.id, min_percent=min_percent, grade=grade))

        # Вопрос с одним правильным ответом (2 балла)
        self.q_single = make_question(self.test, "2+2?", 2, [
            ("3", False), ("4", True), ("5", False),
        ], 1)
        # Вопрос с тремя правильными из пяти (3 балла)
        self.q_multi = make_question(self.test, "Чётные числа", 3, [
            ("2", True), ("4", True), ("6", True), ("7", False), ("9", False),
        ], 2)
        # Ещё два вопроса для банка
        self.q3 = make_question(self.test, "Q3", 1, [("a", True), ("b", False)], 3)
        self.q4 = make_question(self.test, "Q4", 1, [("a", True), ("b", False)], 4)

        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def make_user(self, username, role, group=None):
        user = User(username=username, first_name=username, last_name="Тестов",
                    role=role, group_id=group.id if group else None)
        user.set_password("pass")
        db.session.add(user)
        db.session.flush()
        return user

    def login(self, username):
        self.client.get("/auth/logout")
        return self.client.post("/auth/login", data={"username": username, "password": "pass"})

    def ids(self, question, *texts):
        return [a.id for a in question.answers if a.text in texts]


# =========================================================
# Подсчёт баллов
# =========================================================

class ScoringTests(BaseCase):

    def test_strict_requires_exact_match(self):
        q = self.q_multi
        self.assertEqual(score_question(q, self.ids(q, "2", "4", "6"), "strict"), (3.0, True))
        self.assertEqual(score_question(q, self.ids(q, "2", "4"), "strict"), (0.0, False))
        self.assertEqual(score_question(q, [], "strict"), (0.0, False))

    def test_partial_gives_proportional_points(self):
        q = self.q_multi
        # 2 из 3 верных, без ошибок -> 2/3 от 3 баллов
        self.assertEqual(score_question(q, self.ids(q, "2", "4"), "partial"), (2.0, False))
        # 3 верных + 1 ошибка -> (3-1)/3 = 2/3
        self.assertEqual(score_question(q, self.ids(q, "2", "4", "6", "7"), "partial"), (2.0, False))
        # 1 верный + 1 ошибка -> 0
        self.assertEqual(score_question(q, self.ids(q, "2", "7"), "partial"), (0.0, False))

    def test_partial_selecting_everything_gives_little(self):
        q = self.q_multi
        # 3 верных - 2 ошибки = 1/3 от 3 баллов
        points, full = score_question(q, [a.id for a in q.answers], "partial")
        self.assertEqual((points, full), (1.0, False))

    def test_partial_single_answer_question(self):
        q = self.q_single
        self.assertEqual(score_question(q, self.ids(q, "4"), "partial"), (2.0, True))
        self.assertEqual(score_question(q, self.ids(q, "4", "3"), "partial"), (0.0, False))


# =========================================================
# Выборка и перемешивание
# =========================================================

class LayoutTests(BaseCase):

    def test_no_options_keeps_original_order(self):
        qids, orders = build_attempt_layout(self.test, random.Random(1))
        self.assertEqual(qids, [self.q_single.id, self.q_multi.id, self.q3.id, self.q4.id])
        self.assertEqual(orders[self.q_multi.id], [a.id for a in self.q_multi.answers])

    def test_random_subset_from_bank(self):
        self.test.questions_per_attempt = 2
        seen = set()
        for seed in range(30):
            qids, _ = build_attempt_layout(self.test, random.Random(seed))
            self.assertEqual(len(qids), 2)
            self.assertEqual(len(set(qids)), 2)
            seen.update(qids)
        # За 30 попыток должны встретиться все вопросы банка
        self.assertEqual(len(seen), 4)

    def test_shuffle_changes_order_but_not_content(self):
        self.test.shuffle_questions = True
        self.test.shuffle_answers = True
        orders_seen = set()
        for seed in range(20):
            qids, answers = build_attempt_layout(self.test, random.Random(seed))
            self.assertEqual(sorted(qids), sorted(q.id for q in self.test.questions))
            self.assertEqual(sorted(answers[self.q_multi.id]),
                             sorted(a.id for a in self.q_multi.answers))
            orders_seen.add(tuple(qids))
        self.assertGreater(len(orders_seen), 1)

    def test_limit_larger_than_bank_uses_all(self):
        self.test.questions_per_attempt = 10
        qids, _ = build_attempt_layout(self.test, random.Random(0))
        self.assertEqual(len(qids), 4)


# =========================================================
# Сквозные сценарии через HTTP
# =========================================================

class FlowTests(BaseCase):

    def start(self):
        response = self.client.get(f"/student/test/{self.test.id}/start")
        match = re.search(r"/student/attempt/(\d+)", response.headers.get("Location", ""))
        self.assertIsNotNone(match, "попытка не создана")
        return db.session.get(Attempt, int(match.group(1)))

    def submit(self, attempt, answers):
        data = {}
        for question, texts in answers:
            data[f"question_{question.id}"] = [str(i) for i in self.ids(question, *texts)]
        return self.client.post(f"/student/attempt/{attempt.id}", data=data)

    def test_subset_attempt_scores_only_its_questions(self):
        self.test.questions_per_attempt = 2
        db.session.commit()
        self.login("s1")

        attempt = self.start()
        self.assertEqual(len(attempt.question_ids), 2)

        # Страница показывает ровно 2 вопроса
        page = self.client.get(f"/student/attempt/{attempt.id}").get_data(as_text=True)
        self.assertEqual(page.count('class="question-card"'), 2)

        chosen = [q for q in self.test.questions if q.id in attempt.question_ids]
        self.assertEqual(attempt.max_score, sum(q.points for q in chosen))

        # Отвечаем верно на всё, что досталось
        correct = [(q, [a.text for a in q.answers if a.is_correct]) for q in chosen]
        self.submit(attempt, correct)
        db.session.refresh(attempt)
        self.assertEqual(attempt.percentage, 100)
        self.assertEqual(attempt.grade, 5)

    def test_partial_scoring_end_to_end(self):
        self.test.scoring_mode = "partial"
        db.session.commit()
        self.login("s1")
        attempt = self.start()

        self.submit(attempt, [
            (self.q_single, ["4"]),          # 2 из 2
            (self.q_multi, ["2", "4"]),      # 2 из 3
            (self.q3, ["b"]),                # 0 из 1
        ])
        db.session.refresh(attempt)
        self.assertEqual(attempt.score, 4.0)
        self.assertEqual(attempt.max_score, 7)
        self.assertAlmostEqual(attempt.percentage, 57.14)

    def test_review_reveals_answers_only_after_last_attempt(self):
        self.test.review_mode = "after_all"
        db.session.commit()
        self.login("s1")

        first = self.start()
        self.submit(first, [(self.q_single, ["3"])])
        page = self.client.get(f"/student/result/{first.id}/review").get_data(as_text=True)
        self.assertIn("Разбор ответов", page)
        self.assertNotIn("правильный ответ", page)
        self.assertIn("осталось: 1", page)

        second = self.start()
        self.submit(second, [(self.q_single, ["3"])])
        page = self.client.get(f"/student/result/{second.id}/review").get_data(as_text=True)
        self.assertIn("правильный ответ", page)

    def test_review_disabled(self):
        self.test.review_mode = "none"
        db.session.commit()
        self.login("s1")
        attempt = self.start()
        self.submit(attempt, [])

        result = self.client.get(f"/student/result/{attempt.id}").get_data(as_text=True)
        self.assertNotIn("Разбор ответов", result)
        response = self.client.get(f"/student/result/{attempt.id}/review")
        self.assertEqual(response.status_code, 302)

    def test_review_of_foreign_attempt_is_forbidden(self):
        self.login("s1")
        attempt = self.start()
        self.submit(attempt, [])
        self.login("s2")
        response = self.client.get(f"/student/result/{attempt.id}/review")
        self.assertEqual(response.status_code, 302)

    def test_review_permissions_matrix(self):
        attempt = SimpleNamespace(test=self.test, status="completed")
        cases = {
            ("none", 1): (False, False),
            ("own", 2): (True, False),
            ("always", 1): (True, True),
            ("after_all", 1): (True, False),
            ("after_all", 2): (True, True),
        }
        for (mode, count), expected in cases.items():
            self.test.review_mode = mode
            self.assertEqual(review_permissions(attempt, count), expected, (mode, count))

    def test_late_submission_is_not_counted(self):
        self.login("s1")
        attempt = self.start()
        attempt.started_at -= timedelta(minutes=self.test.time_limit, seconds=45)
        db.session.commit()

        self.submit(attempt, [(self.q_single, ["4"])])
        db.session.refresh(attempt)
        self.assertEqual(attempt.status, "completed")
        self.assertEqual(attempt.score, 0)


class GroupTests(BaseCase):

    def test_test_without_groups_is_visible_to_all(self):
        for username in ("s1", "s2", "s3"):
            self.login(username)
            page = self.client.get("/student/dashboard").get_data(as_text=True)
            self.assertIn("Демо", page, username)

    def test_group_restriction(self):
        self.test.groups = [self.g1]
        db.session.commit()

        self.login("s1")
        self.assertIn("Демо", self.client.get("/student/dashboard").get_data(as_text=True))

        for user in (self.s2, self.s_nogroup):
            self.login(user.username)
            self.assertNotIn("Демо", self.client.get("/student/dashboard").get_data(as_text=True))
            # Прямая ссылка тоже не работает
            self.client.get(f"/student/test/{self.test.id}/start")
            self.assertEqual(Attempt.query.filter_by(student_id=user.id).count(), 0)

    def test_teacher_sets_groups_and_options(self):
        self.login("teacher")
        self.client.post(f"/teacher/test/{self.test.id}/settings", data={
            "title": "Демо 2",
            "time_limit": "15",
            "max_attempts": "",
            "shuffle_questions": "1",
            "questions_per_attempt": "3",
            "scoring_mode": "partial",
            "review_mode": "always",
            "group_ids": [str(self.g2.id)],
        })
        test = db.session.get(Test, self.test.id)
        db.session.refresh(test)
        self.assertEqual(test.title, "Демо 2")
        self.assertIsNone(test.max_attempts)
        self.assertTrue(test.shuffle_questions)
        self.assertFalse(test.shuffle_answers)
        self.assertEqual(test.questions_per_attempt, 3)
        self.assertEqual(test.scoring_mode, "partial")
        self.assertEqual(test.review_mode, "always")
        self.assertEqual([g.name for g in test.groups], ["ПИ-22"])

    def test_admin_manages_groups(self):
        admin = self.make_user("admin", "admin")
        db.session.commit()
        self.login("admin")

        self.client.post("/admin/group/create", data={"name": "МО-23"})
        group = Group.query.filter_by(name="МО-23").one()

        self.client.post(f"/admin/user/{self.s_nogroup.id}/group", data={"group_id": str(group.id)})
        self.assertEqual(db.session.get(User, self.s_nogroup.id).group_id, group.id)

        self.test.groups = [group]
        db.session.commit()

        self.client.post(f"/admin/group/{group.id}/delete")
        self.assertIsNone(Group.query.filter_by(name="МО-23").first())
        self.assertIsNone(db.session.get(User, self.s_nogroup.id).group_id)
        self.assertEqual(db.session.get(Test, self.test.id).groups, [])
        self.assertIsNotNone(admin)

    def test_register_with_group(self):
        self.client.post("/auth/register", data={
            "username": "newbie", "password": "x", "first_name": "Н", "last_name": "Н",
            "group_id": str(self.g2.id),
        })
        self.assertEqual(User.query.filter_by(username="newbie").one().group_id, self.g2.id)


class BestAttemptTests(BaseCase):
    """В статистике учитывается только лучшая попытка по каждому тесту."""

    def pass_twice(self):
        self.login("s1")
        flow = FlowTests.start.__get__(self)
        submit = FlowTests.submit.__get__(self)
        good = flow()
        submit(good, [(q, [a.text for a in q.answers if a.is_correct]) for q in self.test.questions])
        bad = flow()
        submit(bad, [])
        return good, bad

    def test_only_best_is_marked(self):
        good, bad = self.pass_twice()
        db.session.refresh(good)
        db.session.refresh(bad)
        self.assertTrue(good.is_best)
        self.assertFalse(bad.is_best)

    def test_student_stats_use_best(self):
        self.pass_twice()
        page = self.client.get("/student/dashboard").get_data(as_text=True)
        self.assertRegex(page, r"Средний результат</div>\s*<div class=\"stat__value\">\s*100<small>%")

    def test_teacher_results_default_to_best(self):
        self.pass_twice()
        self.login("teacher")
        best = self.client.get("/teacher/results").get_data(as_text=True)
        every = self.client.get("/teacher/results?all=1").get_data(as_text=True)
        self.assertEqual(best.count('class="t-user__name"'), 1)
        self.assertEqual(every.count('class="t-user__name"'), 2)

    def test_admin_grade_distribution_uses_best(self):
        self.pass_twice()
        self.make_user("admin", "admin")
        db.session.commit()
        self.login("admin")
        page = self.client.get("/admin/dashboard").get_data(as_text=True)
        self.assertIn("По лучшей попытке в каждом тесте: 1", page)


if __name__ == "__main__":
    unittest.main()
