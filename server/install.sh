#!/usr/bin/env bash
# Installs or updates the site on a fresh Ubuntu/Debian VPS.
#   curl -fsSL https://raw.githubusercontent.com/smailic05/abduselim-ismailov/main/server/install.sh | sudo bash
set -euo pipefail

REPO=https://github.com/smailic05/abduselim-ismailov.git
DIR=/opt/abduselim-ismailov

if [ "$(id -u)" -ne 0 ]; then echo "Запустите через sudo"; exit 1; fi

if ! command -v git >/dev/null; then apt-get update && apt-get install -y git curl; fi
if ! command -v docker >/dev/null; then curl -fsSL https://get.docker.com | sh; fi

if [ -d "$DIR/.git" ]; then git -C "$DIR" pull --ff-only; else git clone "$REPO" "$DIR"; fi
cd "$DIR/server"

if [ ! -f .env ]; then
  IP=$(curl -fsS https://api.ipify.org || hostname -I | awk '{print $1}')
  echo
  echo "Адрес сайта. Если своего домена нет, нажмите Enter: сайт будет на ${IP}.sslip.io"
  read -r -p "Домен: " DOMAIN </dev/tty
  DOMAIN=${DOMAIN:-${IP}.sslip.io}
  while true; do
    read -r -s -p "Пароль для админки (не короче 8 символов): " PASS </dev/tty; echo
    [ ${#PASS} -ge 8 ] && break
    echo "Слишком короткий."
  done
  umask 077
  cat > .env <<ENV
DOMAIN=${DOMAIN}
ADMIN_PASSWORD=${PASS//\$/\$\$}
SESSION_SECRET=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
SECURE_COOKIE=1
ENV
fi

mkdir -p data
docker compose up -d --build

DOMAIN=$(grep '^DOMAIN=' .env | cut -d= -f2-)
echo
echo "Готово. Сайт: https://${DOMAIN}"
echo "Админка:      https://${DOMAIN}/admin"
