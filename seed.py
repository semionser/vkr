"""
Демо-данные программного комплекса тестирования знаний сотрудников.

Тесты составлены по направлениям работы торгово-промышленной палаты:
основы деятельности палаты, сертификация происхождения товаров,
экспертиза, подтверждение производства продукции и информационная
безопасность для новых сотрудников и практикантов.

Запуск:
    python seed.py            — добавить недостающие демо-данные
    python seed.py --reset    — удалить ВСЕ данные и создать демо-базу заново
                                (спросит подтверждение; --yes — без вопроса)

Скрипт идемпотентен: повторный запуск не создаёт дублей и не меняет
пароли уже существующих пользователей.
Пароль администратора можно задать переменной окружения ADMIN_PASSWORD.
"""

import os
import sys
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
# ГРУППЫ СОТРУДНИКОВ
# =========================================================

GROUPS = [
    {"name": "Эксперты", "description": "Эксперты по сертификации происхождения товаров и экспертизе"},
    {"name": "Новые сотрудники", "description": "Сотрудники в период адаптации"},
    {"name": "Практиканты 2026", "description": "Студенты на производственной и преддипломной практике"},
]


# =========================================================
# ПОЛЬЗОВАТЕЛИ
# role: student — сотрудник, teacher — методист, admin — администратор
# =========================================================

DEMO_PASSWORD = "demo2026"

USERS = [
    {"username": "admin", "first_name": "Администратор", "last_name": "Системы",
     "role": "admin", "email": "admin@example.local",
     "password": os.environ.get("ADMIN_PASSWORD") or "admin2026"},

    {"username": "metodist", "first_name": "Ольга", "last_name": "Кузнецова",
     "role": "teacher", "email": "metodist@example.local"},
    {"username": "kadry", "first_name": "Андрей", "last_name": "Волков",
     "role": "teacher", "email": "kadry@example.local"},

    {"username": "sotrudnik", "first_name": "Пётр", "last_name": "Соколов",
     "role": "student", "email": "sotrudnik@example.local", "group": "Эксперты"},
    {"username": "ekspert", "first_name": "Елена", "last_name": "Морозова",
     "role": "student", "email": "ekspert@example.local", "group": "Эксперты"},
    {"username": "novichok", "first_name": "Анна", "last_name": "Иванова",
     "role": "student", "email": "novichok@example.local", "group": "Новые сотрудники"},
    {"username": "pavlov", "first_name": "Игорь", "last_name": "Павлов",
     "role": "student", "email": "pavlov@example.local", "group": "Новые сотрудники"},
    {"username": "praktikant", "first_name": "Дмитрий", "last_name": "Орлов",
     "role": "student", "email": "praktikant@example.local", "group": "Практиканты 2026"},
]


# =========================================================
# ВСПОМОГАТЕЛЬНОЕ ДЛЯ ОПИСАНИЯ ВОПРОСОВ
# =========================================================

GRADES_60 = [
    {"min_percent": 0,  "grade": 2},
    {"min_percent": 60, "grade": 3},
    {"min_percent": 75, "grade": 4},
    {"min_percent": 90, "grade": 5},
]

GRADES_70 = [
    {"min_percent": 0,  "grade": 2},
    {"min_percent": 70, "grade": 3},
    {"min_percent": 80, "grade": 4},
    {"min_percent": 90, "grade": 5},
]


def q(text, answers, points=1):
    """Вопрос. В answers правильные варианты помечены знаком '+' в начале."""
    return {
        "text": text,
        "points": points,
        "answers": [
            {"text": a[1:].strip() if a.startswith("+") else a,
             "is_correct": a.startswith("+")}
            for a in answers
        ],
    }


# =========================================================
# НАПРАВЛЕНИЯ И ТЕСТЫ
# =========================================================

SUBJECTS = [
    # -----------------------------------------------------
    {
        "name": "Основы деятельности ТПП",
        "description": "Правовой статус, задачи и органы управления торгово-промышленных палат",
        "tests": [
            {
                "title": "Основы деятельности ТПП РФ",
                "description": "Вводный тест для новых сотрудников и практикантов",
                "time_limit": 15, "passing_score": 60, "max_attempts": 3,
                "status": "published", "grades": GRADES_60,
                "options": {"shuffle_questions": True, "shuffle_answers": True,
                            "questions_per_attempt": 6, "review_mode": "after_all"},
                "questions": [
                    q("Какой нормативный акт определяет правовой статус торгово-промышленных палат в Российской Федерации?", [
                        "+Закон РФ от 07.07.1993 № 5340-1 «О торгово-промышленных палатах в Российской Федерации»",
                        "Федеральный закон № 44-ФЗ «О контрактной системе…»",
                        "Федеральный закон № 223-ФЗ «О закупках товаров, работ, услуг отдельными видами юридических лиц»",
                        "Гражданский кодекс РФ, часть четвёртая",
                    ]),
                    q("К какому виду организаций относится торгово-промышленная палата?", [
                        "+Негосударственная некоммерческая организация",
                        "Федеральный орган исполнительной власти",
                        "Государственное бюджетное учреждение",
                        "Коммерческая организация (акционерное общество)",
                    ]),
                    q("Как соотносится ответственность палаты и государства по обязательствам друг друга?", [
                        "+Государство не отвечает по обязательствам палат, а палаты — по обязательствам государства",
                        "Государство отвечает по обязательствам палат",
                        "Палаты отвечают по обязательствам государства",
                        "Ответственность солидарная",
                    ]),
                    q("Какой орган является высшим органом управления ТПП РФ?", [
                        "+Съезд ТПП РФ",
                        "Правление ТПП РФ",
                        "Президент ТПП РФ",
                        "Ревизионная комиссия",
                    ]),
                    q("Какие из перечисленных услуг оказывает система ТПП? (несколько ответов)", [
                        "+Удостоверение сертификатов о происхождении товаров",
                        "+Проведение экспертизы качества, количества и комплектности товаров",
                        "+Свидетельствование обстоятельств непреодолимой силы (форс-мажора)",
                        "Государственная регистрация юридических лиц",
                        "Выдача лицензий на банковскую деятельность",
                    ], points=2),
                    q("Какая организация свидетельствует обстоятельства непреодолимой силы по внешнеторговым сделкам?", [
                        "+Торгово-промышленная палата Российской Федерации",
                        "Федеральная налоговая служба",
                        "Министерство иностранных дел",
                        "Нотариальная палата",
                    ]),
                    q("Какой постоянно действующий арбитражный орган образован при ТПП РФ?", [
                        "+Международный коммерческий арбитражный суд (МКАС)",
                        "Верховный суд РФ",
                        "Арбитражный суд города Москвы",
                        "Конституционный суд РФ",
                    ]),
                    q("Кто может быть членами территориальной торгово-промышленной палаты?", [
                        "+Организации и индивидуальные предприниматели",
                        "Только государственные предприятия",
                        "Только иностранные компании",
                        "Только физические лица без статуса ИП",
                    ]),
                ],
            },
        ],
    },

    # -----------------------------------------------------
    {
        "name": "Сертификация происхождения товаров",
        "description": "Формы сертификатов, критерии происхождения и порядок удостоверения",
        "tests": [
            {
                "title": "Сертификат СТ-1 и критерии происхождения",
                "description": "Правила определения страны происхождения товаров в СНГ",
                "time_limit": 20, "passing_score": 70, "max_attempts": 2,
                "status": "published", "grades": GRADES_70,
                "options": {"shuffle_questions": True, "shuffle_answers": True,
                            "scoring_mode": "partial", "review_mode": "after_all",
                            "groups": ["Эксперты"]},
                "questions": [
                    q("Для вывоза товаров в какие страны используется сертификат о происхождении формы СТ-1?", [
                        "+В государства — участники Соглашения о зоне свободной торговли СНГ",
                        "В страны Европейского союза",
                        "В любые страны мира без исключения",
                        "Только в Китай",
                    ]),
                    q("Какая организация в России удостоверяет сертификаты о происхождении формы СТ-1?", [
                        "+Уполномоченные торгово-промышленные палаты",
                        "Федеральная таможенная служба",
                        "Министерство финансов",
                        "Любой нотариус",
                    ]),
                    q("При каких условиях товар считается происходящим из данной страны? (несколько ответов)", [
                        "+Товар полностью произведён в этой стране",
                        "+Товар подвергнут в этой стране достаточной переработке",
                        "Товар прошёл через эту страну транзитом",
                        "Товар упакован в этой стране",
                    ], points=2),
                    q("Какие из перечисленных операций НЕ считаются достаточной переработкой? (несколько ответов)", [
                        "+Упаковка и переупаковка",
                        "+Сортировка и простая сборка",
                        "+Нанесение маркировки",
                        "Изменение товарной позиции по ТН ВЭД в результате переработки",
                    ], points=2),
                    q("Какой из критериев используется для определения достаточной переработки?", [
                        "+Изменение классификационного кода товара по ТН ВЭД на уровне любого из первых четырёх знаков",
                        "Изменение цвета упаковки",
                        "Смена поставщика",
                        "Перевозка товара другим видом транспорта",
                    ]),
                    q("Какие товары считаются полностью произведёнными в стране? (несколько ответов)", [
                        "+Полезные ископаемые, добытые на её территории",
                        "+Живые животные, родившиеся и выращенные в ней",
                        "+Растения, выращенные на её территории",
                        "Изделия, собранные из импортных комплектующих без изменения кода ТН ВЭД",
                    ], points=2),
                    q("Сертификат о происхождении какой формы оформляется, если преференции не предоставляются, но документ нужен по условиям контракта или требованию страны ввоза?", [
                        "+Сертификат общей формы",
                        "Сертификат формы СТ-1",
                        "Декларация о соответствии",
                        "Паспорт сделки",
                    ]),
                ],
            },
            {
                "title": "Порядок оформления сертификата",
                "description": "Документы заявителя и проверка перед удостоверением",
                "time_limit": 15, "passing_score": 60, "max_attempts": None,
                "status": "published", "grades": GRADES_60,
                "options": {"shuffle_answers": True, "review_mode": "always",
                            "groups": ["Эксперты", "Новые сотрудники"]},
                "questions": [
                    q("С чего начинается оформление сертификата о происхождении?", [
                        "+С подачи заявителем заявления и комплекта документов",
                        "С выезда эксперта на склад без заявки",
                        "С оплаты таможенной пошлины",
                        "С регистрации товара в ФНС",
                    ]),
                    q("Какие документы обычно прикладываются к заявлению на сертификат? (несколько ответов)", [
                        "+Коммерческие документы по сделке (контракт, счёт-фактура, инвойс)",
                        "+Документы, подтверждающие происхождение товара",
                        "Трудовая книжка руководителя",
                        "Паспорт каждого сотрудника заявителя",
                    ], points=2),
                    q("Что должен сделать сотрудник, если сведения в заявлении не совпадают с коммерческими документами?", [
                        "+Не удостоверять сертификат до устранения расхождений",
                        "Удостоверить сертификат, так как отвечает заявитель",
                        "Исправить документы заявителя самостоятельно",
                        "Выдать сертификат с пометкой «черновик»",
                    ]),
                    q("Кто вправе проводить экспертизу по определению страны происхождения в системе ТПП?", [
                        "+Эксперт, прошедший обучение и аттестацию в системе ТПП",
                        "Любой сотрудник палаты",
                        "Представитель заявителя",
                        "Сотрудник банка, обслуживающего сделку",
                    ]),
                ],
            },
        ],
    },

    # -----------------------------------------------------
    {
        "name": "Экспертиза товаров",
        "description": "Виды экспертиз и оформление их результатов",
        "tests": [
            {
                "title": "Виды экспертиз и акт экспертизы",
                "description": "Базовые понятия экспертной деятельности палаты",
                "time_limit": 15, "passing_score": 60, "max_attempts": 3,
                "status": "published", "grades": GRADES_60,
                "options": {"shuffle_questions": True, "shuffle_answers": True,
                            "review_mode": "after_all", "groups": ["Эксперты"]},
                "questions": [
                    q("Какие виды экспертиз проводит система ТПП? (несколько ответов)", [
                        "+Экспертиза качества товара",
                        "+Экспертиза количества и комплектности",
                        "+Экспертиза по определению страны происхождения",
                        "Судебно-медицинская экспертиза",
                    ], points=2),
                    q("Каким документом оформляются результаты экспертизы?", [
                        "+Актом экспертизы",
                        "Протоколом собрания",
                        "Приказом по палате",
                        "Счётом-фактурой",
                    ]),
                    q("На каком основании эксперт приступает к работе?", [
                        "+На основании заявки заказчика и поручения палаты",
                        "По устной просьбе знакомого",
                        "По собственной инициативе",
                        "По звонку перевозчика",
                    ]),
                    q("Что эксперт должен сделать при отсутствии доступа к товару или необходимых документов?", [
                        "+Зафиксировать это и не делать выводов, которые нельзя подтвердить",
                        "Составить акт по фотографиям из интернета",
                        "Перенести выводы из прошлой экспертизы",
                        "Подписать акт, оставив выводы пустыми",
                    ]),
                    q("Почему эксперт должен быть независимым от сторон сделки?", [
                        "+Чтобы выводы экспертизы были объективными и им доверяли обе стороны",
                        "Чтобы экспертиза стоила дешевле",
                        "Потому что так быстрее",
                        "Независимость не требуется",
                    ]),
                ],
            },
        ],
    },

    # -----------------------------------------------------
    {
        "name": "Подтверждение производства продукции",
        "description": "Российская промышленная продукция и документы для государственных закупок",
        "tests": [
            {
                "title": "Постановление Правительства РФ № 719",
                "description": "Подтверждение производства промышленной продукции на территории РФ",
                "time_limit": 10, "passing_score": 60, "max_attempts": 2,
                "status": "published", "grades": GRADES_60,
                "options": {"shuffle_answers": True, "review_mode": "own",
                            "groups": ["Эксперты", "Новые сотрудники"]},
                "questions": [
                    q("Какой документ устанавливает требования к промышленной продукции для подтверждения её производства на территории РФ?", [
                        "+Постановление Правительства РФ от 17.07.2015 № 719",
                        "Закон РФ № 5340-1",
                        "Федеральный закон № 152-ФЗ",
                        "Трудовой кодекс РФ",
                    ]),
                    q("Какое министерство ведёт реестр российской промышленной продукции?", [
                        "+Министерство промышленности и торговли РФ",
                        "Министерство финансов РФ",
                        "Министерство цифрового развития РФ",
                        "Министерство юстиции РФ",
                    ]),
                    q("В какой государственной информационной системе размещается реестр российской промышленной продукции?", [
                        "+ГИСП — государственная информационная система промышленности",
                        "ЕГРЮЛ",
                        "ЕИС в сфере закупок как единственный источник",
                        "Система «Честный знак»",
                    ]),
                    q("Для чего производителю нужно подтверждение производства продукции в России?", [
                        "+Чтобы участвовать в закупках с мерами поддержки российской продукции",
                        "Чтобы получить заграничный паспорт",
                        "Чтобы не платить налоги",
                        "Чтобы зарегистрировать товарный знак",
                    ]),
                ],
            },
        ],
    },

    # -----------------------------------------------------
    {
        "name": "Информационная безопасность",
        "description": "Правила работы с информацией для сотрудников и практикантов",
        "tests": [
            {
                "title": "Информационная безопасность на рабочем месте",
                "description": "Пароли, фишинг и работа с учётными записями",
                "time_limit": 10, "passing_score": 70, "max_attempts": None,
                "status": "published", "grades": GRADES_70,
                "options": {"shuffle_questions": True, "shuffle_answers": True,
                            "review_mode": "always",
                            "groups": ["Новые сотрудники", "Практиканты 2026"]},
                "questions": [
                    q("Какой пароль можно считать надёжным?", [
                        "+Не короче 8 символов, с буквами разного регистра, цифрами и знаками",
                        "Дата рождения",
                        "Слово «password»",
                        "Логин, записанный наоборот",
                    ]),
                    q("Пришло письмо «срочно подтвердите пароль по ссылке». Что нужно сделать?", [
                        "+Не переходить по ссылке и сообщить в ИТ-отдел",
                        "Перейти и ввести пароль, раз просят срочно",
                        "Переслать письмо коллегам",
                        "Ответить отправителю своим паролем",
                    ]),
                    q("Можно ли передать свою учётную запись коллеге на время отпуска?", [
                        "+Нет, каждый работает только под своей учётной записью",
                        "Да, если коллега из того же отдела",
                        "Да, если записать пароль на бумаге",
                        "Да, с разрешения любого сотрудника",
                    ]),
                    q("Какое сочетание клавиш блокирует компьютер с Windows, когда вы отходите от рабочего места?", [
                        "+Win + L",
                        "Ctrl + C",
                        "Alt + Tab",
                        "Win + D",
                    ]),
                    q("Какие действия помогают защитить рабочий компьютер? (несколько ответов)", [
                        "+Блокировать экран, уходя с рабочего места",
                        "+Не подключать неизвестные флешки",
                        "+Устанавливать программы только через ИТ-отдел",
                        "Отключать антивирус, чтобы компьютер работал быстрее",
                    ], points=2),
                ],
            },
            {
                "title": "Персональные данные и электронная подпись",
                "description": "Основы 152-ФЗ и 63-ФЗ для сотрудников",
                "time_limit": 10, "passing_score": 60, "max_attempts": 3,
                "status": "draft", "grades": GRADES_60,
                "options": {"shuffle_answers": True, "review_mode": "after_all"},
                "questions": [
                    q("Какой федеральный закон регулирует обработку персональных данных?", [
                        "+Федеральный закон № 152-ФЗ «О персональных данных»",
                        "Федеральный закон № 63-ФЗ «Об электронной подписи»",
                        "Закон РФ № 5340-1",
                        "Федеральный закон № 44-ФЗ",
                    ]),
                    q("Что относится к персональным данным? (несколько ответов)", [
                        "+Фамилия, имя и отчество",
                        "+Паспортные данные",
                        "+Номер телефона конкретного человека",
                        "Курс валют на сегодня",
                    ], points=2),
                    q("Какой федеральный закон регулирует использование электронной подписи?", [
                        "+Федеральный закон № 63-ФЗ «Об электронной подписи»",
                        "Федеральный закон № 152-ФЗ",
                        "Гражданский кодекс РФ, часть первая",
                        "Налоговый кодекс РФ",
                    ]),
                    q("Можно ли передавать свой ключ электронной подписи другому человеку?", [
                        "+Нет, ключ электронной подписи хранится в тайне и используется только владельцем",
                        "Да, если это руководитель",
                        "Да, по электронной почте",
                        "Да, если подпись просрочена",
                    ]),
                ],
            },
        ],
    },
]


# Демо-попытки: (логин, название теста, доля верных ответов, сколько дней назад)
DEMO_ATTEMPTS = [
    ("sotrudnik",  "Основы деятельности ТПП РФ",                  1.00, 18),
    ("sotrudnik",  "Сертификат СТ-1 и критерии происхождения",    0.72, 12),
    ("sotrudnik",  "Виды экспертиз и акт экспертизы",             0.60, 6),
    ("ekspert",    "Основы деятельности ТПП РФ",                  0.88, 15),
    ("ekspert",    "Сертификат СТ-1 и критерии происхождения",    0.86, 9),
    ("ekspert",    "Порядок оформления сертификата",              1.00, 4),
    ("ekspert",    "Постановление Правительства РФ № 719",        0.75, 2),
    ("novichok",   "Основы деятельности ТПП РФ",                  0.63, 10),
    ("novichok",   "Информационная безопасность на рабочем месте", 0.80, 3),
    ("pavlov",     "Основы деятельности ТПП РФ",                  0.38, 8),
    ("pavlov",     "Информационная безопасность на рабочем месте", 1.00, 1),
    ("praktikant", "Основы деятельности ТПП РФ",                  0.75, 5),
    ("praktikant", "Информационная безопасность на рабочем месте", 0.60, 1),
]


# =========================================================
# ХЕЛПЕРЫ
# =========================================================

def get_or_create_user(data, groups_by_name):
    user = User.query.filter_by(username=data["username"]).first()
    created = user is None

    if created:
        user = User(username=data["username"])
        user.set_password(data.get("password") or DEMO_PASSWORD)
        db.session.add(user)

    # Пароль существующего пользователя не меняем
    user.first_name = data["first_name"]
    user.last_name = data["last_name"]
    user.role = data["role"]
    user.email = data["email"]
    if data.get("group"):
        user.group_id = groups_by_name[data["group"]].id

    db.session.flush()
    return user, "created" if created else "updated"


def get_or_create_group(data):
    group = Group.query.filter_by(name=data["name"]).first()

    if group is None:
        group = Group(name=data["name"], description=data["description"])
        db.session.add(group)
        db.session.flush()
        return group, "created"

    group.description = data["description"]
    return group, "updated"


def get_or_create_subject(data):
    subject = Subject.query.filter_by(name=data["name"]).first()

    if subject is None:
        subject = Subject(name=data["name"], description=data["description"])
        db.session.add(subject)
        db.session.flush()
        return subject, "created"

    subject.description = data["description"]
    return subject, "updated"


def apply_test_options(test, options, groups_by_name):
    for key in ("shuffle_questions", "shuffle_answers",
                "questions_per_attempt", "scoring_mode", "review_mode"):
        if key in options:
            setattr(test, key, options[key])

    if "groups" in options:
        test.groups = [groups_by_name[name] for name in options["groups"]]


def get_or_create_test(subject, author, data, groups_by_name):
    test = Test.query.filter_by(subject_id=subject.id, title=data["title"]).first()

    if test is not None:
        return test, "exists"

    test = Test(
        subject_id=subject.id,
        teacher_id=author.id,
        title=data["title"],
        description=data["description"],
        time_limit=data["time_limit"],
        passing_score=data["passing_score"],
        max_attempts=data["max_attempts"],
        status=data["status"],
    )
    db.session.add(test)
    db.session.flush()

    for qi, qd in enumerate(data["questions"], start=1):
        question = Question(test_id=test.id, text=qd["text"],
                            points=qd["points"], question_order=qi)
        db.session.add(question)
        db.session.flush()

        for ai, ad in enumerate(qd["answers"], start=1):
            db.session.add(Answer(question_id=question.id, text=ad["text"],
                                  is_correct=ad["is_correct"], answer_order=ai))

    for g in data["grades"]:
        db.session.add(TestGrade(test_id=test.id, min_percent=g["min_percent"], grade=g["grade"]))

    apply_test_options(test, data.get("options", {}), groups_by_name)
    db.session.flush()
    return test, "created"


def grade_for(test, percentage):
    rule = (
        TestGrade.query
        .filter(TestGrade.test_id == test.id, TestGrade.min_percent <= percentage)
        .order_by(TestGrade.min_percent.desc())
        .first()
    )
    return rule.grade if rule else 2


def create_demo_attempt(test, user, correct_ratio, days_ago):
    """Завершённая попытка: первые correct_ratio вопросов отвечены верно."""
    if Attempt.query.filter_by(test_id=test.id, student_id=user.id).first():
        return None, "exists"

    questions = sorted(test.questions, key=lambda x: x.question_order)
    if not questions:
        return None, "empty"

    finished = datetime.utcnow() - timedelta(days=days_ago, hours=(days_ago * 7) % 9)
    max_score = sum(x.points for x in questions)
    correct_count = min(len(questions), max(0, round(len(questions) * correct_ratio)))

    attempt = Attempt(
        test_id=test.id,
        student_id=user.id,
        started_at=finished - timedelta(minutes=min(test.time_limit, 4 + len(questions))),
        completed_at=finished,
        score=0,
        max_score=max_score,
        percentage=0,
        status="in_progress",
        is_best=False,
    )
    db.session.add(attempt)
    db.session.flush()

    score = 0
    for idx, question in enumerate(questions):
        is_correct = idx < correct_count
        chosen = [a for a in question.answers if a.is_correct == is_correct]
        if not is_correct:
            chosen = chosen[:1]
        for answer in chosen:
            db.session.add(StudentAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                answer_id=answer.id,
                is_correct=is_correct,
                points=question.points if is_correct and answer is chosen[0] else 0,
            ))
        if is_correct:
            score += question.points

    attempt.score = score
    attempt.percentage = round(score / max_score * 100, 2) if max_score else 0
    attempt.grade = grade_for(test, attempt.percentage)
    attempt.status = "completed"
    attempt.is_best = True
    db.session.flush()
    return attempt, "created"


# =========================================================
# ГЛАВНАЯ
# =========================================================

def seed(reset=False):
    app = create_app()

    with app.app_context():
        print("=" * 64)
        print("  Демо-данные: тестирование знаний сотрудников")
        print("=" * 64)

        if reset:
            print("\n! --reset: все таблицы удаляются и создаются заново")
            db.drop_all()
            db.create_all()

        print("\nГруппы:")
        groups_by_name = {}
        for data in GROUPS:
            group, action = get_or_create_group(data)
            groups_by_name[group.name] = group
            print(f"  {'+' if action == 'created' else '·'} {group.name}")

        print("\nПользователи:")
        users = {}
        for data in USERS:
            user, action = get_or_create_user(data, groups_by_name)
            users[user.username] = user
            role = {"student": "сотрудник", "teacher": "методист", "admin": "администратор"}[user.role]
            print(f"  {'+' if action == 'created' else '·'} {user.username:<11} {role:<14} "
                  f"{user.last_name} {user.first_name}")

        author = users["metodist"]

        print("\nНаправления и тесты:")
        tests = {}
        for s_data in SUBJECTS:
            subject, action = get_or_create_subject(s_data)
            print(f"  {'+' if action == 'created' else '·'} {subject.name}")
            for t_data in s_data["tests"]:
                test, t_action = get_or_create_test(subject, author, t_data, groups_by_name)
                tests[test.title] = test
                print(f"      {'+' if t_action == 'created' else '·'} {test.title} "
                      f"({len(test.questions)} вопр., {test.time_limit} мин)")

        print("\nДемо-попытки:")
        for username, title, ratio, days_ago in DEMO_ATTEMPTS:
            attempt, action = create_demo_attempt(tests[title], users[username], ratio, days_ago)
            if attempt:
                print(f"  + {username:<11} {title}: {attempt.percentage:g}% — оценка {attempt.grade}")

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print(f"\n✗ Ошибка при сохранении: {exc}")
            sys.exit(1)

        print("\n✓ Готово. Вход для демонстрации:")
        print("  admin      — администратор"
              + ("" if os.environ.get("ADMIN_PASSWORD") else " (пароль admin2026)"))
        print(f"  metodist   — методист        (пароль {DEMO_PASSWORD})")
        print(f"  sotrudnik  — сотрудник       (пароль {DEMO_PASSWORD})")
        print(f"  praktikant — практикант      (пароль {DEMO_PASSWORD})")
        print("  Пароли уже существующих пользователей не изменялись.")


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    if reset and "--yes" not in sys.argv:
        answer = input("Все пользователи, тесты и результаты будут удалены. Продолжить? (да/нет): ")
        if answer.strip().lower() not in ("да", "yes", "y", "д"):
            print("Отменено.")
            sys.exit(0)
    seed(reset=reset)
