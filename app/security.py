"""
Защита веб-приложения.

* секретный ключ из переменной окружения или файла instance/secret_key;
* CSRF-токен для каждого POST-запроса;
* разграничение доступа по ролям на уровне blueprint'ов;
* ограничение числа неудачных попыток входа;
* безопасные параметры cookie и HTTP-заголовки.
"""

import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from functools import wraps
from pathlib import Path

from flask import abort, current_app, request, session
from flask_login import current_user
from markupsafe import Markup


# =========================================================
# SECRET KEY
# =========================================================

def load_secret_key(instance_path):
    """
    SECRET_KEY берётся из переменной окружения. Если её нет — из файла
    instance/secret_key, который создаётся автоматически при первом запуске
    и не попадает в git. Ключ больше не хранится в исходном коде.
    """
    key = os.environ.get("SECRET_KEY")
    if key:
        return key

    path = Path(instance_path) / "secret_key"
    if path.exists():
        return path.read_text().strip()

    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    path.write_text(key)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


# =========================================================
# CSRF
# =========================================================

CSRF_FIELD = "csrf_token"
CSRF_SESSION_KEY = "_csrf_token"


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def csrf_input():
    """Скрытое поле с токеном для вставки в форму: {{ csrf_input() }}"""
    return Markup(
        f'<input type="hidden" name="{CSRF_FIELD}" value="{get_csrf_token()}">'
    )


def check_csrf():
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    if not current_app.config.get("CSRF_ENABLED", True):
        return

    sent = request.form.get(CSRF_FIELD) or request.headers.get("X-CSRF-Token", "")
    expected = session.get(CSRF_SESSION_KEY, "")

    if not expected or not sent or not hmac.compare_digest(sent, expected):
        abort(400, description="Форма устарела или отправлена с чужого сайта. "
                               "Обновите страницу и попробуйте ещё раз.")


# =========================================================
# ROLES
# =========================================================

def require_role(blueprint, role):
    """
    Все маршруты blueprint'а доступны только авторизованному
    пользователю с указанной ролью. Проверка в одном месте, а не
    в каждой функции: новый маршрут невозможно «забыть» защитить.
    """
    @blueprint.before_request
    def _guard():
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if current_user.role != role:
            abort(403)


def role_required(*roles):
    """Декоратор для отдельных маршрутов вне ролевых blueprint'ов."""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorator


# =========================================================
# LOGIN RATE LIMIT
# =========================================================

class LoginLimiter:
    """
    Не более MAX_FAILS неудачных входов за WINDOW секунд
    для пары «логин + IP». Хранится в памяти процесса.
    """

    MAX_FAILS = 5
    WINDOW = 5 * 60

    def __init__(self):
        self._fails = defaultdict(deque)

    def _key(self, username):
        return f"{(username or '').lower()}|{request.remote_addr}"

    def _prune(self, q, now):
        while q and now - q[0] > self.WINDOW:
            q.popleft()

    def blocked_for(self, username):
        """Сколько секунд осталось до разблокировки (0 — не заблокирован)."""
        q = self._fails[self._key(username)]
        now = time.time()
        self._prune(q, now)
        if len(q) >= self.MAX_FAILS:
            return int(self.WINDOW - (now - q[0])) + 1
        return 0

    def fail(self, username):
        q = self._fails[self._key(username)]
        self._prune(q, time.time())
        q.append(time.time())

    def reset(self, username):
        self._fails.pop(self._key(username), None)


login_limiter = LoginLimiter()


# =========================================================
# HEADERS
# =========================================================

def set_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    if current_app.config.get("SESSION_COOKIE_SECURE"):
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


# =========================================================
# INIT
# =========================================================

def init_security(app):
    app.jinja_env.globals["csrf_token"] = get_csrf_token
    app.jinja_env.globals["csrf_input"] = csrf_input
    app.before_request(check_csrf)
    app.after_request(set_security_headers)
