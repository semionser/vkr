#!/usr/bin/env bash
# =====================================================================
#  Развёртывание Student Testing System на Ubuntu 22.04 / 24.04
#
#  Запуск на сервере под root:
#     bash install.sh                      # по IP, без HTTPS
#     DOMAIN=sts.example.ru EMAIL=me@mail.ru bash install.sh   # с HTTPS
#
#  Что делает:
#   1. Ставит Python, nginx, git, certbot, файрвол
#   2. Создаёт системного пользователя sts и скачивает проект с GitHub
#   3. Создаёт виртуальное окружение и ставит зависимости
#   4. Создаёт .env с секретным ключом и базу с демо-данными
#   5. Запускает приложение через gunicorn как службу systemd
#   6. Настраивает nginx как обратный прокси и (с доменом) HTTPS
#
#  Повторный запуск безопасен: существующие база и .env не трогаются.
# =====================================================================
set -euo pipefail

REPO="${REPO:-https://github.com/semionser/vkr.git}"
BRANCH="${BRANCH:-main}"
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"

APP_USER="sts"
APP_DIR="/opt/sts"
DATA_DIR="/var/lib/sts"
SERVICE="sts"

step() { echo; echo "==> $*"; }

if [[ $EUID -ne 0 ]]; then
    echo "Запустите скрипт от root: sudo bash install.sh" >&2
    exit 1
fi

# ---------------------------------------------------------------------
step "1/7 Установка системных пакетов"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q python3 python3-venv python3-pip git nginx ufw \
    certbot python3-certbot-nginx

# ---------------------------------------------------------------------
step "2/7 Пользователь и код приложения"
id -u "$APP_USER" &>/dev/null || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$DATA_DIR"

if [[ -d "$APP_DIR/.git" ]]; then
    git -c safe.directory="$APP_DIR" -C "$APP_DIR" fetch -q origin "$BRANCH"
    git -c safe.directory="$APP_DIR" -C "$APP_DIR" reset -q --hard "origin/$BRANCH"
else
    git clone -q --branch "$BRANCH" "$REPO" "$APP_DIR"
fi

if [[ ! -f "$APP_DIR/wsgi.py" ]]; then
    echo "В репозитории нет wsgi.py — сначала отправьте на GitHub обновление безопасности." >&2
    exit 1
fi

# ---------------------------------------------------------------------
step "3/7 Виртуальное окружение и зависимости"
[[ -d "$APP_DIR/.venv" ]] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt" gunicorn

# ---------------------------------------------------------------------
step "4/7 Настройки (.env)"
ENV_FILE="$APP_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > "$ENV_FILE" <<ENV
SECRET_KEY=$SECRET
DATABASE_URL=sqlite:///$DATA_DIR/database.db
BEHIND_PROXY=1
HTTPS=$([[ -n "$DOMAIN" ]] && echo 1 || echo 0)
ENV
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$DATA_DIR"
chmod 600 "$ENV_FILE"
chmod 750 "$DATA_DIR"

# ---------------------------------------------------------------------
step "5/7 База данных"
ADMIN_PASSWORD=""
if [[ ! -f "$DATA_DIR/database.db" ]]; then
    cd "$APP_DIR"
    sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" seed.py > /dev/null

    # Демо-пароль администратора заменяется случайным
    ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(12))")
    sudo -u "$APP_USER" ADMIN_PASSWORD="$ADMIN_PASSWORD" "$APP_DIR/.venv/bin/python" - <<'PY'
import os
from app import create_app, db
from app.models import User
app = create_app()
with app.app_context():
    admin = User.query.filter_by(username="admin").first()
    admin.set_password(os.environ["ADMIN_PASSWORD"])
    db.session.commit()
PY
else
    echo "База уже существует — оставляю как есть."
fi

# ---------------------------------------------------------------------
step "6/7 Служба gunicorn (systemd)"
cat > "/etc/systemd/system/$SERVICE.service" <<UNIT
[Unit]
Description=Student Testing System (gunicorn)
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$APP_DIR/.venv/bin/gunicorn --workers 2 --threads 4 \\
    --bind 127.0.0.1:8000 --access-logfile - --error-logfile - wsgi:app
Restart=always
RestartSec=3

# Ограничения безопасности для службы
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=$DATA_DIR $APP_DIR/instance

[Install]
WantedBy=multi-user.target
UNIT

mkdir -p "$APP_DIR/instance" && chown "$APP_USER:$APP_USER" "$APP_DIR/instance"
systemctl daemon-reload
systemctl enable -q "$SERVICE"
systemctl restart "$SERVICE"

# ---------------------------------------------------------------------
step "7/7 nginx, файрвол и HTTPS"
SERVER_NAME="${DOMAIN:-_}"
cat > /etc/nginx/sites-available/sts <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $SERVER_NAME;

    client_max_body_size 2m;
    server_tokens off;

    location /static/ {
        alias $APP_DIR/app/static/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/sts /etc/nginx/sites-enabled/sts
rm -f /etc/nginx/sites-enabled/default
nginx -t -q
systemctl reload nginx

ufw allow OpenSSH > /dev/null
ufw allow "Nginx Full" > /dev/null
ufw --force enable > /dev/null

if [[ -n "$DOMAIN" ]]; then
    if [[ -n "$EMAIL" ]]; then
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
    else
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
            --register-unsafely-without-email --redirect
    fi
fi

# ---------------------------------------------------------------------
sleep 2
echo
echo "=================================================================="
if systemctl is-active -q "$SERVICE" && curl -fsS -o /dev/null http://127.0.0.1:8000/; then
    echo "  ✓ Приложение запущено"
else
    echo "  ✗ Приложение не отвечает. Журнал: journalctl -u $SERVICE -n 50"
fi

IP=$(curl -fsS -4 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
if [[ -n "$DOMAIN" ]]; then
    echo "  Адрес: https://$DOMAIN"
else
    echo "  Адрес: http://$IP"
fi

if [[ -n "$ADMIN_PASSWORD" ]]; then
    echo
    echo "  Администратор: admin / $ADMIN_PASSWORD"
    echo "  Сохраните пароль — больше он показан не будет."
    echo "  Демо-аккаунты teacher/teacher123 и student/student123 — смените пароли"
    echo "  или удалите их через панель администратора."
fi
echo "=================================================================="
