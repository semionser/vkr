#!/usr/bin/env bash
# Обновление сайта до последней версии из GitHub (запуск под root).
#     bash /opt/sts/deploy/update.sh
set -euo pipefail

APP_DIR="/opt/sts"
BRANCH="${BRANCH:-main}"

git -c safe.directory="$APP_DIR" -C "$APP_DIR" fetch -q origin "$BRANCH"
git -c safe.directory="$APP_DIR" -C "$APP_DIR" reset -q --hard "origin/$BRANCH"
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt" gunicorn
chown -R sts:sts "$APP_DIR"
chmod 600 "$APP_DIR/.env"
systemctl restart sts

sleep 2
if systemctl is-active -q sts; then
    echo "✓ Обновлено: $(git -c safe.directory="$APP_DIR" -C "$APP_DIR" log -1 --format='%h %s')"
else
    echo "✗ Служба не запустилась: journalctl -u sts -n 50"
fi
