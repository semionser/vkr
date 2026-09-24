"""
Точка входа для WSGI-сервера (gunicorn, uWSGI, PythonAnywhere).

    gunicorn wsgi:app
"""

import os

from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app

app = create_app()

# За обратным прокси (nginx) Flask должен видеть исходные схему и адрес
# клиента: это нужно для правильных ссылок, HTTPS-cookie и лимита входа по IP.
if os.environ.get("BEHIND_PROXY") == "1":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
