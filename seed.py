"""
Сид-скрипт: создаёт демо-данные для Student Testing System.

Запуск:
    python seed.py

Идемпотентен — можно запускать многократно без дублей.
"""

from datetime import datetime, timedelta

from app import create_app, db
from app.models import (
    Group,
    User,
    Subject,
    Test,
    Question,
    Answer,
    TestGrade,
    Attempt,
    StudentAnswer,
)


# =========================================================
# УЧЕБНЫЕ ГРУППЫ
# =========================================================

GROUPS = [
    {"name": "ИВТ-21", "description": "Информатика и вычислительная техника"},
    {"name": "ПИ-22",  "description": "Прикладная информатика"},
]

# Логин студента -> группа
STUDENT_GROUPS = {
    "student":  "ИВТ-21",
    "student2": "ПИ-22",
}

# Дополнительные параметры отдельных тестов (для демонстрации)
TEST_OPTIONS = {
    "Основы Python": {
        "shuffle_questions": True,
        "shuffle_answers": True,
        "scoring_mode": "partial",
        "review_mode": "after_all",
    },
    "Алгоритмы сортировки": {
        "shuffle_questions": True,
        "shuffle_answers": True,
        "questions_per_attempt": 3,
        "review_mode": "always",
    },
    # Тест только для группы ПИ-22 — студент из ИВТ-21 его не увидит
    "Лексика и идиомы": {
        "groups": ["ПИ-22"],
    },
}


# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================

USERS = [
    {
        "username":   "admin",
        "first_name": "Администратор",
        "last_name":  "Системы",
        "role":       "admin",
        "email":      "admin@example.local",
        "password":   "admin123",
    },
    {
        "username":   "teacher",
        "first_name": "Иван",
        "last_name":  "Преподаватель",
        "role":       "teacher",
        "email":      "teacher@example.local",
        "password":   "teacher123",
    },
    {
        "username":   "teacher2",
        "first_name": "Мария",
        "last_name":  "Смирнова",
        "role":       "teacher",
        "email":      "teacher2@example.local",
        "password":   "teacher123",
    },
    {
        "username":   "student",
        "first_name": "Пётр",
        "last_name":  "Студентов",
        "role":       "student",
        "email":      "student@example.local",
        "password":   "student123",
    },
    {
        "username":   "student2",
        "first_name": "Анна",
        "last_name":  "Иванова",
        "role":       "student",
        "email":      "student2@example.local",
        "password":   "student123",
    },
]


# =========================================================
# ДИСЦИПЛИНЫ + ТЕСТЫ
# =========================================================

SUBJECTS = [
    # =====================================================
    # 1. ПРОГРАММИРОВАНИЕ — 4 теста
    # =====================================================
    {
        "name": "Программирование",
        "description": "Основы программирования, ООП и алгоритмы",
        "tests": [
            {
                "title": "Основы Python",
                "description": "Базовый синтаксис, типы данных и конструкции языка",
                "time_limit": 20,
                "passing_score": 60,
                "max_attempts": 3,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 60, "grade": 3},
                    {"min_percent": 75, "grade": 4},
                    {"min_percent": 90, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Какой оператор используется для вывода на экран в Python?",
                        "points": 1,
                        "answers": [
                            {"text": "print()",              "is_correct": True},
                            {"text": "echo()",               "is_correct": False},
                            {"text": "console.log()",        "is_correct": False},
                            {"text": "System.out.println()", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какой тип данных в Python является неизменяемым?",
                        "points": 1,
                        "answers": [
                            {"text": "list",  "is_correct": False},
                            {"text": "tuple", "is_correct": True},
                            {"text": "dict",  "is_correct": False},
                            {"text": "set",   "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какой результат выражения 2 ** 3 в Python?",
                        "points": 1,
                        "answers": [
                            {"text": "5", "is_correct": False},
                            {"text": "6", "is_correct": False},
                            {"text": "8", "is_correct": True},
                            {"text": "9", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Как объявить функцию в Python?",
                        "points": 1,
                        "answers": [
                            {"text": "function myFunc():", "is_correct": False},
                            {"text": "def myFunc():",      "is_correct": True},
                            {"text": "func myFunc():",     "is_correct": False},
                            {"text": "void myFunc():",     "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что делает метод append() у списка?",
                        "points": 1,
                        "answers": [
                            {"text": "Добавляет элемент в конец списка", "is_correct": True},
                            {"text": "Удаляет последний элемент",        "is_correct": False},
                            {"text": "Сортирует список",                 "is_correct": False},
                            {"text": "Очищает список",                   "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Объектно-ориентированное программирование",
                "description": "Классы, наследование, инкапсуляция, полиморфизм",
                "time_limit": 30,
                "passing_score": 70,
                "max_attempts": 2,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 70, "grade": 3},
                    {"min_percent": 80, "grade": 4},
                    {"min_percent": 95, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Какой принцип ООП скрывает внутреннее состояние объекта?",
                        "points": 2,
                        "answers": [
                            {"text": "Инкапсуляция",   "is_correct": True},
                            {"text": "Наследование",   "is_correct": False},
                            {"text": "Полиморфизм",    "is_correct": False},
                            {"text": "Абстракция",     "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что такое конструктор класса?",
                        "points": 2,
                        "answers": [
                            {"text": "Метод, вызываемый при создании объекта", "is_correct": True},
                            {"text": "Метод, удаляющий объект",               "is_correct": False},
                            {"text": "Статический метод",                     "is_correct": False},
                            {"text": "Приватное поле класса",                 "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какой принцип позволяет использовать один интерфейс для разных типов?",
                        "points": 2,
                        "answers": [
                            {"text": "Полиморфизм",  "is_correct": True},
                            {"text": "Инкапсуляция", "is_correct": False},
                            {"text": "Наследование", "is_correct": False},
                            {"text": "Композиция",   "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что означает ключевое слово super в Python?",
                        "points": 2,
                        "answers": [
                            {"text": "Ссылка на родительский класс",  "is_correct": True},
                            {"text": "Ссылка на текущий класс",       "is_correct": False},
                            {"text": "Ссылка на модуль",              "is_correct": False},
                            {"text": "Создание нового объекта",       "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Алгоритмы сортировки",
                "description": "Пузырьковая, быстрая, слиянием",
                "time_limit": 25,
                "passing_score": 70,
                "max_attempts": 2,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 70, "grade": 3},
                    {"min_percent": 80, "grade": 4},
                    {"min_percent": 95, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Какая сложность у пузырьковой сортировки в худшем случае?",
                        "points": 1,
                        "answers": [
                            {"text": "O(n)",       "is_correct": False},
                            {"text": "O(n log n)", "is_correct": False},
                            {"text": "O(n^2)",     "is_correct": True},
                            {"text": "O(log n)",   "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какая сортировка использует стратегию «разделяй и властвуй»?",
                        "points": 1,
                        "answers": [
                            {"text": "Пузырьковая", "is_correct": False},
                            {"text": "Быстрая",     "is_correct": True},
                            {"text": "Вставками",   "is_correct": False},
                            {"text": "Выбором",     "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какая сортировка гарантирует O(n log n) в любом случае?",
                        "points": 1,
                        "answers": [
                            {"text": "Быстрая",     "is_correct": False},
                            {"text": "Слиянием",    "is_correct": True},
                            {"text": "Пузырьковая", "is_correct": False},
                            {"text": "Выбором",     "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что такое устойчивая сортировка?",
                        "points": 1,
                        "answers": [
                            {"text": "Сохраняет порядок равных элементов", "is_correct": True},
                            {"text": "Работает за O(n)",                   "is_correct": False},
                            {"text": "Не использует дополнительную память","is_correct": False},
                            {"text": "Работает только с числами",          "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Структуры данных",
                "description": "Списки, стеки, очереди, деревья, хеш-таблицы",
                "time_limit": 40,
                "passing_score": 65,
                "max_attempts": None,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 65, "grade": 3},
                    {"min_percent": 80, "grade": 4},
                    {"min_percent": 92, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Какая структура данных работает по принципу LIFO?",
                        "points": 2,
                        "answers": [
                            {"text": "Стек",   "is_correct": True},
                            {"text": "Очередь","is_correct": False},
                            {"text": "Список","is_correct": False},
                            {"text": "Дерево","is_correct": False},
                        ],
                    },
                    {
                        "text": "Какая структура данных работает по принципу FIFO?",
                        "points": 2,
                        "answers": [
                            {"text": "Очередь", "is_correct": True},
                            {"text": "Стек",    "is_correct": False},
                            {"text": "Куча",    "is_correct": False},
                            {"text": "Граф",    "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какая сложность поиска в сбалансированном бинарном дереве?",
                        "points": 2,
                        "answers": [
                            {"text": "O(log n)", "is_correct": True},
                            {"text": "O(n)",     "is_correct": False},
                            {"text": "O(1)",     "is_correct": False},
                            {"text": "O(n^2)",   "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что такое хеш-таблица?",
                        "points": 2,
                        "answers": [
                            {"text": "Структура, хранящая пары ключ-значение", "is_correct": True},
                            {"text": "Список чисел",                          "is_correct": False},
                            {"text": "Дерево поиска",                         "is_correct": False},
                            {"text": "Очередь с приоритетом",                 "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },

    # =====================================================
    # 2. МАТЕМАТИКА — 3 теста
    # =====================================================
    {
        "name": "Математика",
        "description": "Дискретная математика и линейная алгебра",
        "tests": [
            {
                "title": "Линейная алгебра",
                "description": "Матрицы, определители, системы уравнений",
                "time_limit": 30,
                "passing_score": 60,
                "max_attempts": None,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 60, "grade": 3},
                    {"min_percent": 75, "grade": 4},
                    {"min_percent": 90, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Чему равен определитель единичной матрицы 3×3?",
                        "points": 2,
                        "answers": [
                            {"text": "0", "is_correct": False},
                            {"text": "1", "is_correct": True},
                            {"text": "3", "is_correct": False},
                            {"text": "9", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какое условие нужно для существования обратной матрицы?",
                        "points": 2,
                        "answers": [
                            {"text": "Определитель не равен нулю", "is_correct": True},
                            {"text": "Все элементы положительны",  "is_correct": False},
                            {"text": "Матрица квадратная",         "is_correct": False},
                            {"text": "Матрица симметричная",       "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что такое ранг матрицы?",
                        "points": 2,
                        "answers": [
                            {"text": "Максимальное число линейно независимых строк", "is_correct": True},
                            {"text": "Количество строк",                             "is_correct": False},
                            {"text": "Сумма элементов главной диагонали",            "is_correct": False},
                            {"text": "Определитель матрицы",                         "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Дискретная математика",
                "description": "Множества, логика, комбинаторика, графы",
                "time_limit": 45,
                "passing_score": 55,
                "max_attempts": 3,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 55, "grade": 3},
                    {"min_percent": 70, "grade": 4},
                    {"min_percent": 85, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Сколько подмножеств имеет множество из 4 элементов?",
                        "points": 2,
                        "answers": [
                            {"text": "8",  "is_correct": False},
                            {"text": "12", "is_correct": False},
                            {"text": "16", "is_correct": True},
                            {"text": "24", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Чему равно число сочетаний C(5, 2)?",
                        "points": 2,
                        "answers": [
                            {"text": "5",  "is_correct": False},
                            {"text": "10", "is_correct": True},
                            {"text": "15", "is_correct": False},
                            {"text": "20", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какое логическое выражение тождественно A ∧ (A ∨ B)?",
                        "points": 2,
                        "answers": [
                            {"text": "A",       "is_correct": True},
                            {"text": "B",       "is_correct": False},
                            {"text": "A ∨ B",   "is_correct": False},
                            {"text": "A ∧ B",   "is_correct": False},
                        ],
                    },
                    {
                        "text": "Сколько рёбер в полном графе на 5 вершинах?",
                        "points": 2,
                        "answers": [
                            {"text": "5",  "is_correct": False},
                            {"text": "10", "is_correct": True},
                            {"text": "15", "is_correct": False},
                            {"text": "20", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Математический анализ",
                "description": "Пределы, производные, интегралы",
                "time_limit": 60,
                "passing_score": 60,
                "max_attempts": 2,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 60, "grade": 3},
                    {"min_percent": 75, "grade": 4},
                    {"min_percent": 90, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Чему равна производная функции x²?",
                        "points": 2,
                        "answers": [
                            {"text": "x",  "is_correct": False},
                            {"text": "2x", "is_correct": True},
                            {"text": "x²", "is_correct": False},
                            {"text": "2",  "is_correct": False},
                        ],
                    },
                    {
                        "text": "Чему равен интеграл ∫ 2x dx?",
                        "points": 2,
                        "answers": [
                            {"text": "x² + C", "is_correct": True},
                            {"text": "2 + C",  "is_correct": False},
                            {"text": "2x + C", "is_correct": False},
                            {"text": "x + C",  "is_correct": False},
                        ],
                    },
                    {
                        "text": "Чему равен предел lim(x→0) sin(x)/x?",
                        "points": 2,
                        "answers": [
                            {"text": "0", "is_correct": False},
                            {"text": "1", "is_correct": True},
                            {"text": "∞", "is_correct": False},
                            {"text": "не существует", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что означает непрерывность функции в точке?",
                        "points": 2,
                        "answers": [
                            {"text": "Предел функции в точке равен значению функции в этой точке", "is_correct": True},
                            {"text": "Функция принимает только положительные значения",           "is_correct": False},
                            {"text": "Функция определена на всём множестве",                     "is_correct": False},
                            {"text": "Производная функции существует",                           "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },

    # =====================================================
    # 3. ФИЗИКА — 3 теста
    # =====================================================
    {
        "name": "Физика",
        "description": "Механика, термодинамика, электродинамика",
        "tests": [
            {
                "title": "Механика",
                "description": "Кинематика и динамика",
                "time_limit": 20,
                "passing_score": 50,
                "max_attempts": 5,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 50, "grade": 3},
                    {"min_percent": 70, "grade": 4},
                    {"min_percent": 85, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Второй закон Ньютона в векторной форме:",
                        "points": 1,
                        "answers": [
                            {"text": "F = ma", "is_correct": True},
                            {"text": "F = mv", "is_correct": False},
                            {"text": "F = m/a","is_correct": False},
                            {"text": "F = a/m","is_correct": False},
                        ],
                    },
                    {
                        "text": "Чему равно ускорение свободного падения на Земле (≈)?",
                        "points": 1,
                        "answers": [
                            {"text": "5.8 м/с²",  "is_correct": False},
                            {"text": "9.8 м/с²",  "is_correct": True},
                            {"text": "12 м/с²",   "is_correct": False},
                            {"text": "3.14 м/с²", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Формула кинетической энергии:",
                        "points": 1,
                        "answers": [
                            {"text": "mv²/2", "is_correct": True},
                            {"text": "mv",    "is_correct": False},
                            {"text": "mgh",   "is_correct": False},
                            {"text": "ma",    "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Термодинамика",
                "description": "Законы термодинамики, теплота, энтропия",
                "time_limit": 35,
                "passing_score": 60,
                "max_attempts": 2,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 60, "grade": 3},
                    {"min_percent": 75, "grade": 4},
                    {"min_percent": 90, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Сколько законов термодинамики существует?",
                        "points": 2,
                        "answers": [
                            {"text": "1", "is_correct": False},
                            {"text": "2", "is_correct": False},
                            {"text": "3", "is_correct": True},
                            {"text": "4", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что утверждает первое начало термодинамики?",
                        "points": 2,
                        "answers": [
                            {"text": "Закон сохранения энергии для тепловых процессов", "is_correct": True},
                            {"text": "Энтропия замкнутой системы не убывает",            "is_correct": False},
                            {"text": "Абсолютный ноль недостижим",                      "is_correct": False},
                            {"text": "Теплота самопроизвольно переходит от холодного к горячему", "is_correct": False},
                        ],
                    },
                    {
                        "text": "В чём измеряется температура в СИ?",
                        "points": 2,
                        "answers": [
                            {"text": "В градусах Цельсия", "is_correct": False},
                            {"text": "В кельвинах",        "is_correct": True},
                            {"text": "В градусах Фаренгейта", "is_correct": False},
                            {"text": "В джоулях",          "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что такое энтропия?",
                        "points": 2,
                        "answers": [
                            {"text": "Мера неупорядоченности системы", "is_correct": True},
                            {"text": "Количество теплоты",             "is_correct": False},
                            {"text": "Внутренняя энергия",             "is_correct": False},
                            {"text": "Работа газа",                    "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Электродинамика",
                "description": "Электрические и магнитные явления",
                "time_limit": 45,
                "passing_score": 55,
                "max_attempts": 3,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 55, "grade": 3},
                    {"min_percent": 72, "grade": 4},
                    {"min_percent": 88, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Закон Ома для участка цепи:",
                        "points": 2,
                        "answers": [
                            {"text": "I = U/R", "is_correct": True},
                            {"text": "I = UR",  "is_correct": False},
                            {"text": "I = R/U", "is_correct": False},
                            {"text": "I = U²R", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Единица измерения силы тока:",
                        "points": 2,
                        "answers": [
                            {"text": "Вольт", "is_correct": False},
                            {"text": "Ампер", "is_correct": True},
                            {"text": "Ом",    "is_correct": False},
                            {"text": "Ватт",  "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что создаёт магнитное поле?",
                        "points": 2,
                        "answers": [
                            {"text": "Движущиеся заряды",  "is_correct": True},
                            {"text": "Неподвижные заряды", "is_correct": False},
                            {"text": "Массы",              "is_correct": False},
                            {"text": "Только постоянные магниты", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },

    # =====================================================
    # 4. ИСТОРИЯ — 3 теста
    # =====================================================
    {
        "name": "История",
        "description": "Всемирная история и история России",
        "tests": [
            {
                "title": "Древний мир",
                "description": "Цивилизации древности",
                "time_limit": 25,
                "passing_score": 50,
                "max_attempts": 5,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 50, "grade": 3},
                    {"min_percent": 70, "grade": 4},
                    {"min_percent": 85, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "В каком году основан Рим?",
                        "points": 1,
                        "answers": [
                            {"text": "753 до н.э.", "is_correct": True},
                            {"text": "500 до н.э.", "is_correct": False},
                            {"text": "1000 до н.э.","is_correct": False},
                            {"text": "100 н.э.",    "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какое из семи чудес света сохранилось до наших дней?",
                        "points": 1,
                        "answers": [
                            {"text": "Пирамида Хеопса",          "is_correct": True},
                            {"text": "Висячие сады Семирамиды",  "is_correct": False},
                            {"text": "Колосс Родосский",         "is_correct": False},
                            {"text": "Александрийский маяк",     "is_correct": False},
                        ],
                    },
                    {
                        "text": "Как называлась письменность в Древнем Египте?",
                        "points": 1,
                        "answers": [
                            {"text": "Клинопись",      "is_correct": False},
                            {"text": "Иероглифы",      "is_correct": True},
                            {"text": "Алфавит",        "is_correct": False},
                            {"text": "Руны",           "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Средние века",
                "description": "Европа и Восток в V–XV веках",
                "time_limit": 30,
                "passing_score": 55,
                "max_attempts": 4,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 55, "grade": 3},
                    {"min_percent": 72, "grade": 4},
                    {"min_percent": 88, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "В каком году произошло разделение христианской церкви?",
                        "points": 2,
                        "answers": [
                            {"text": "1054",  "is_correct": True},
                            {"text": "988",   "is_correct": False},
                            {"text": "1204",  "is_correct": False},
                            {"text": "1453",  "is_correct": False},
                        ],
                    },
                    {
                        "text": "Кто возглавил первый крестовый поход?",
                        "points": 2,
                        "answers": [
                            {"text": "Готфрид Бульонский", "is_correct": True},
                            {"text": "Ричард Львиное Сердце", "is_correct": False},
                            {"text": "Фридрих Барбаросса", "is_correct": False},
                            {"text": "Людовик IX",         "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что такое феодализм?",
                        "points": 2,
                        "answers": [
                            {"text": "Система землевладения с вассальной иерархией", "is_correct": True},
                            {"text": "Форма правления с выборным королём",           "is_correct": False},
                            {"text": "Религиозное движение",                        "is_correct": False},
                            {"text": "Военная стратегия",                           "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Новейшая история",
                "description": "XX–XXI века",
                "time_limit": 40,
                "passing_score": 60,
                "max_attempts": 3,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 60, "grade": 3},
                    {"min_percent": 75, "grade": 4},
                    {"min_percent": 90, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "В каком году началась Вторая мировая война?",
                        "points": 2,
                        "answers": [
                            {"text": "1914", "is_correct": False},
                            {"text": "1939", "is_correct": True},
                            {"text": "1941", "is_correct": False},
                            {"text": "1945", "is_correct": False},
                        ],
                    },
                    {
                        "text": "В каком году человек впервые полетел в космос?",
                        "points": 2,
                        "answers": [
                            {"text": "1957", "is_correct": False},
                            {"text": "1961", "is_correct": True},
                            {"text": "1969", "is_correct": False},
                            {"text": "1975", "is_correct": False},
                        ],
                    },
                    {
                        "text": "В каком году распался Советский Союз?",
                        "points": 2,
                        "answers": [
                            {"text": "1985", "is_correct": False},
                            {"text": "1989", "is_correct": False},
                            {"text": "1991", "is_correct": True},
                            {"text": "1993", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что такое холодная война?",
                        "points": 2,
                        "answers": [
                            {"text": "Политическое противостояние США и СССР", "is_correct": True},
                            {"text": "Военный конфликт на севере Европы",       "is_correct": False},
                            {"text": "Экономический кризис 1930-х",            "is_correct": False},
                            {"text": "Научная гонка в Антарктиде",              "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },

    # =====================================================
    # 5. АНГЛИЙСКИЙ ЯЗЫК — 2 теста
    # =====================================================
    {
        "name": "Английский язык",
        "description": "Грамматика и лексика английского языка",
        "tests": [
            {
                "title": "Времена английского глагола",
                "description": "Present, Past, Future",
                "time_limit": 15,
                "passing_score": 60,
                "max_attempts": 4,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 60, "grade": 3},
                    {"min_percent": 75, "grade": 4},
                    {"min_percent": 90, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Какое время используется для описания регулярных действий?",
                        "points": 1,
                        "answers": [
                            {"text": "Present Simple",       "is_correct": True},
                            {"text": "Present Continuous",   "is_correct": False},
                            {"text": "Past Simple",          "is_correct": False},
                            {"text": "Future Simple",        "is_correct": False},
                        ],
                    },
                    {
                        "text": "Как образуется Present Perfect?",
                        "points": 1,
                        "answers": [
                            {"text": "have/has + V3", "is_correct": True},
                            {"text": "be + Ving",     "is_correct": False},
                            {"text": "will + V",      "is_correct": False},
                            {"text": "did + V",       "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какая форма глагола используется в Past Simple у правильных глаголов?",
                        "points": 1,
                        "answers": [
                            {"text": "V + ed",      "is_correct": True},
                            {"text": "V + ing",     "is_correct": False},
                            {"text": "V + s",       "is_correct": False},
                            {"text": "have + V3",   "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Лексика и идиомы",
                "description": "Словарный запас, устойчивые выражения",
                "time_limit": 20,
                "passing_score": 65,
                "max_attempts": 3,
                "status": "published",
                "grades": [
                    {"min_percent": 0,  "grade": 2},
                    {"min_percent": 65, "grade": 3},
                    {"min_percent": 80, "grade": 4},
                    {"min_percent": 92, "grade": 5},
                ],
                "questions": [
                    {
                        "text": "Что означает идиома «break a leg»?",
                        "points": 2,
                        "answers": [
                            {"text": "Пожелание удачи", "is_correct": True},
                            {"text": "Сломать ногу",    "is_correct": False},
                            {"text": "Пойти танцевать", "is_correct": False},
                            {"text": "Упасть",          "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что означает слово «ubiquitous»?",
                        "points": 2,
                        "answers": [
                            {"text": "Вездесущий",    "is_correct": True},
                            {"text": "Огромный",      "is_correct": False},
                            {"text": "Опасный",       "is_correct": False},
                            {"text": "Необычный",     "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что означает идиома «hit the books»?",
                        "points": 2,
                        "answers": [
                            {"text": "Усердно учиться", "is_correct": True},
                            {"text": "Бить книги",      "is_correct": False},
                            {"text": "Портить вещи",    "is_correct": False},
                            {"text": "Читать вслух",    "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
]


# =========================================================
# ХЕЛПЕРЫ
# =========================================================

def get_or_create_user(data):
    user = User.query.filter_by(username=data["username"]).first()

    if user is None:
        user = User(
            username=data["username"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            role=data["role"],
            email=data["email"],
        )
        user.set_password(data["password"])
        db.session.add(user)
        db.session.flush()
        return user, "created"

    user.first_name = data["first_name"]
    user.last_name  = data["last_name"]
    user.role       = data["role"]
    user.email      = data["email"]
    user.set_password(data["password"])
    return user, "updated"


def get_or_create_group(data):
    group = Group.query.filter_by(name=data["name"]).first()

    if group is None:
        group = Group(name=data["name"], description=data["description"])
        db.session.add(group)
        db.session.flush()
        return group, "created"

    group.description = data["description"]
    return group, "updated"


def apply_test_options(test, groups_by_name):
    options = TEST_OPTIONS.get(test.title)
    if not options:
        return

    for key in ("shuffle_questions", "shuffle_answers",
                "questions_per_attempt", "scoring_mode", "review_mode"):
        if key in options:
            setattr(test, key, options[key])

    if "groups" in options:
        test.groups = [groups_by_name[name] for name in options["groups"]]


def get_or_create_subject(data):
    subject = Subject.query.filter_by(name=data["name"]).first()

    if subject is None:
        subject = Subject(
            name=data["name"],
            description=data["description"],
        )
        db.session.add(subject)
        db.session.flush()
        return subject, "created"

    subject.description = data["description"]
    return subject, "updated"


def get_or_create_test(subject, teacher, data):
    test = Test.query.filter_by(
        subject_id=subject.id,
        title=data["title"],
    ).first()

    if test is not None:
        test.description   = data["description"]
        test.time_limit    = data["time_limit"]
        test.passing_score = data["passing_score"]
        test.max_attempts  = data["max_attempts"]
        test.status        = data["status"]
        return test, "exists"

    test = Test(
        subject_id=subject.id,
        teacher_id=teacher.id,
        title=data["title"],
        description=data["description"],
        time_limit=data["time_limit"],
        passing_score=data["passing_score"],
        max_attempts=data["max_attempts"],
        status=data["status"],
    )
    db.session.add(test)
    db.session.flush()

    for qi, q in enumerate(data["questions"], start=1):
        question = Question(
            test_id=test.id,
            text=q["text"],
            points=q["points"],
            question_order=qi,
        )
        db.session.add(question)
        db.session.flush()

        for ai, a in enumerate(q["answers"], start=1):
            db.session.add(Answer(
                question_id=question.id,
                text=a["text"],
                is_correct=a["is_correct"],
                answer_order=ai,
            ))

    for g in data["grades"]:
        db.session.add(TestGrade(
            test_id=test.id,
            min_percent=g["min_percent"],
            grade=g["grade"],
        ))

    db.session.flush()
    return test, "created"


def create_demo_attempt(test, student, correct_ratio=0.7):
    """
    Создаёт завершённую попытку.
    correct_ratio: доля правильных ответов (0..1).
    """
    existing = Attempt.query.filter_by(
        test_id=test.id,
        student_id=student.id,
    ).first()

    if existing:
        return existing, "exists"

    questions = sorted(test.questions, key=lambda q: q.question_order)
    if not questions:
        return None, "empty"

    max_score = sum(q.points for q in questions)
    total_questions = len(questions)

    # Сколько вопросов делаем правильными
    correct_count = max(1, int(round(total_questions * correct_ratio)))
    correct_count = min(correct_count, total_questions)

    attempt = Attempt(
        test_id=test.id,
        student_id=student.id,
        started_at=datetime.utcnow() - timedelta(minutes=15),
        completed_at=datetime.utcnow() - timedelta(minutes=5),
        score=0,
        max_score=max_score,
        percentage=0,
        grade=None,
        status="in_progress",
        is_best=False,
    )
    db.session.add(attempt)
    db.session.flush()

    score = 0

    for idx, question in enumerate(questions):
        is_correct = idx < correct_count

        if is_correct:
            answer = next((a for a in question.answers if a.is_correct), None)
            points = question.points if answer else 0
        else:
            answer = next((a for a in question.answers if not a.is_correct), None)
            points = 0

        if answer is None:
            continue

        db.session.add(StudentAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            answer_id=answer.id,
            is_correct=is_correct,
            points=points,
        ))

        if is_correct:
            score += points

    attempt.score = score
    attempt.percentage = round((score / max_score) * 100, 2) if max_score else 0

    grade_rule = (
        TestGrade.query
        .filter(
            TestGrade.test_id == test.id,
            TestGrade.min_percent <= attempt.percentage,
        )
        .order_by(TestGrade.min_percent.desc())
        .first()
    )
    attempt.grade = grade_rule.grade if grade_rule else 2
    attempt.status = "completed"
    attempt.is_best = True

    db.session.flush()
    return attempt, "created"


# =========================================================
# ГЛАВНАЯ
# =========================================================

def seed():
    app = create_app()

    with app.app_context():
        print("=" * 64)
        print("  Запуск сид-скрипта Student Testing System")
        print("=" * 64)
        print()

        # ---------- Пользователи ----------
        users_by_name = {}

        print("Пользователи:")
        for data in USERS:
            user, action = get_or_create_user(data)
            users_by_name[user.username] = user
            marker = "＋" if action == "created" else "↻"
            print(f"  {marker} {user.username:<12} ({user.role:<10}) — "
                  f"{user.last_name} {user.first_name} | {data['password']}")

        teacher  = users_by_name["teacher"]
        student  = users_by_name["student"]

        print()

        # ---------- Группы ----------
        print("Учебные группы:")
        groups_by_name = {}
        for data in GROUPS:
            group, action = get_or_create_group(data)
            groups_by_name[group.name] = group
            marker = "＋" if action == "created" else "↻"
            print(f"  {marker} {group.name}")

        for username, group_name in STUDENT_GROUPS.items():
            if username in users_by_name:
                users_by_name[username].group_id = groups_by_name[group_name].id
                print(f"      {username} → {group_name}")

        print()

        # ---------- Дисциплины, тесты, вопросы ----------
        print("Дисциплины и тесты:")

        created_tests = []

        for s_data in SUBJECTS:
            subject, s_action = get_or_create_subject(s_data)
            s_marker = "＋" if s_action == "created" else "↻"

            print(f"  {s_marker} {subject.name}")

            for t_data in s_data["tests"]:
                test, t_action = get_or_create_test(subject, teacher, t_data)
                apply_test_options(test, groups_by_name)
                t_marker = "＋" if t_action == "created" else "·"

                attempts_label = (
                    "∞" if test.max_attempts is None
                    else str(test.max_attempts)
                )

                print(f"      {t_marker} {test.title} — "
                      f"{len(test.questions)} вопр., "
                      f"{test.time_limit} мин., "
                      f"попыток: {attempts_label}")

                if t_action == "created":
                    created_tests.append(test)

        print()

        # ---------- Демо-попытки ----------
        print("Демо-попытки студента:")

        # Раскладываем попытки с разным процентом для наглядности
        attempt_plan = [
            (0, 1.0),   # 100%
            (1, 0.75),  # 75%
            (2, 0.5),   # 50%
            (3, 0.25),  # 25%
            (4, 0.9),   # 90%
            (5, 0.6),   # 60%
        ]

        for idx, ratio in attempt_plan:
            if idx >= len(created_tests):
                break

            test = created_tests[idx]
            attempt, action = create_demo_attempt(test, student, correct_ratio=ratio)

            if attempt is None:
                continue

            marker = "＋" if action == "created" else "·"
            print(f"  {marker} {test.title}: "
                  f"{attempt.score}/{attempt.max_score} "
                  f"({attempt.percentage}%) — оценка {attempt.grade}")

        print()

        # ---------- Коммит ----------
        try:
            db.session.commit()
            print("=" * 64)
            print("  ✓ Все данные сохранены.")
            print("=" * 64)
            print()
            print("Логины для входа:")
            print("  admin    / admin123")
            print("  teacher  / teacher123")
            print("  teacher2 / teacher123")
            print("  student  / student123")
            print("  student2 / student123")
        except Exception as e:
            db.session.rollback()
            print("=" * 64)
            print("  ✗ Ошибка при сохранении:")
            print(f"  {e}")
            print("=" * 64)


if __name__ == "__main__":
    seed()