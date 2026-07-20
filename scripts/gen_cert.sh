#!/usr/bin/env bash
# Generates a self-signed HTTPS certificate for the machine's LAN IP so phone
# browsers will allow camera access (getUserMedia requires a secure context
# for any origin that isn't localhost).
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p certs

LAN_IP="$(hostname -I | awk '{print $1}')"
if [ -z "$LAN_IP" ]; then
  echo "Could not determine LAN IP via 'hostname -I'. Set LAN_IP manually and re-run." >&2
  exit 1
fi

echo "Generating self-signed certificate for ${LAN_IP} (and 127.0.0.1)..."
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout certs/key.pem -out certs/cert.pem \
  -days 365 \
  -subj "/CN=${LAN_IP}" \
  -addext "subjectAltName=IP:${LAN_IP},IP:127.0.0.1"

echo "Done. certs/cert.pem and certs/key.pem written."
echo "Run ./run.sh, then open https://${LAN_IP}:8000 on your phone (same Wi-Fi)."
