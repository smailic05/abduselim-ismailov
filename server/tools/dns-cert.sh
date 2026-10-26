#!/usr/bin/env bash
# Gets the HTTPS certificate through Timeweb DNS instead of a connection to this server.
# Use it when Let's Encrypt cannot reach the server (Caddy logs "Timeout after connect").
#   sudo bash /opt/abduselim-ismailov/server/tools/dns-cert.sh
set -euo pipefail
cd "$(dirname "$0")/.."
DIR=$(pwd)

DOMAINS=$(grep '^DOMAIN=' .env | cut -d= -f2- | tr ',' ' ')
ARGS=""
for d in $DOMAINS; do ARGS="$ARGS -d $d"; done
MAIN=$(echo $DOMAINS | awk '{print $1}')

if [ ! -x ~/.acme.sh/acme.sh ]; then
  command -v cron >/dev/null || (apt-get update && apt-get install -y cron)
  rm -rf /tmp/acme.sh && git clone --depth 1 https://github.com/acmesh-official/acme.sh.git /tmp/acme.sh
  (cd /tmp/acme.sh && ./acme.sh --install)
fi

if [ -z "${TW_Token:-}" ]; then
  echo "Нужен API-токен Timeweb Cloud: панель → API и Terraform → Создать токен."
  read -r -s -p "API-токен (при вводе не отображается): " TW_Token </dev/tty; echo
fi
export TW_Token

~/.acme.sh/acme.sh --issue --server letsencrypt --dns dns_timeweb $ARGS --keylength ec-256 || [ $? -eq 2 ]

mkdir -p certs
grep -q '^CADDY_TLS=' .env || echo 'CADDY_TLS=tls /certs/fullchain.pem /certs/key.pem' >> .env
~/.acme.sh/acme.sh --install-cert -d "$MAIN" --ecc \
  --key-file "$DIR/certs/key.pem" --fullchain-file "$DIR/certs/fullchain.pem" \
  --reloadcmd "cd $DIR && docker compose restart caddy"
docker compose up -d caddy

echo
echo "Готово. Сертификат будет продлеваться сам. Сайт: https://$MAIN"
