#!/usr/bin/env bash
# Runs the AI Gym Trainer server over HTTPS on the LAN so a phone browser can
# connect and use its camera. Generate certs first with ./scripts/gen_cert.sh
# if certs/cert.pem and certs/key.pem don't exist yet.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f certs/cert.pem ] || [ ! -f certs/key.pem ]; then
  echo "No certs found, generating them now..."
  ./scripts/gen_cert.sh
fi

LAN_IP="$(hostname -I | awk '{print $1}')"
PORT="${PORT:-8000}"

echo "Starting server at https://${LAN_IP}:${PORT}  (open this URL on your phone, same Wi-Fi)"
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --ssl-keyfile certs/key.pem \
  --ssl-certfile certs/cert.pem
