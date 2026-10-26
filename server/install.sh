#!/usr/bin/env bash
# Installs or updates the site on a fresh Ubuntu/Debian VPS.
#   curl -fsSL https://raw.githubusercontent.com/smailic05/abduselim-ismailov/main/server/install.sh | sudo bash
set -euo pipefail

REPO=https://github.com/smailic05/abduselim-ismailov.git
DIR=/opt/abduselim-ismailov
BRANCH=${BRANCH:-main}

if [ "$(id -u)" -ne 0 ]; then echo "Запустите через sudo"; exit 1; fi

if ! command -v git >/dev/null; then apt-get update && apt-get install -y git curl; fi
if ! command -v docker >/dev/null; then curl -fsSL https://get.docker.com | sh; fi

# Docker Hub is unreachable from some networks (for example Russian hosting); pull through mirrors, falling back to Hub
if [ ! -f /etc/docker/daemon.json ]; then
  mkdir -p /etc/docker
  echo '{"registry-mirrors":["https://mirror.gcr.io","https://dockerhub.timeweb.cloud"]}' > /etc/docker/daemon.json
  systemctl restart docker
fi

if [ -d "$DIR/.git" ]; then
  git -C "$DIR" fetch origin "$BRANCH" && git -C "$DIR" checkout -B "$BRANCH" "origin/$BRANCH"
else
  git clone -b "$BRANCH" "$REPO" "$DIR"
fi
cd "$DIR/server"

if [ ! -f .env ]; then
  IP=$(curl -fsS https://api.ipify.org || hostname -I | awk '{print $1}')
  echo
  echo "Адрес сайта. Если своего домена нет, нажмите Enter: сайт будет на ${IP}.sslip.io"
  while true; do
    read -r -p "Домен: " DOMAIN </dev/tty
    DOMAIN=${DOMAIN:-${IP}.sslip.io}
    [[ "$DOMAIN" == *.* ]] && break
    echo "Это не домен. Введите купленный домен вроде example.ru или просто нажмите Enter."
  done
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

# open web ports if the firewall is on
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then ufw allow 80/tcp; ufw allow 443; fi

docker compose up -d --build

DOMAIN=$(grep '^DOMAIN=' .env | cut -d= -f2-)
echo
echo "Готово. Сайт: https://${DOMAIN}"
echo "Админка:      https://${DOMAIN}/admin"
