#!/usr/bin/env bash
# Obtiene el certificado SSL de Let's Encrypt (ejecutar una vez en EC2 con nginx levantado en :80).
# Uso: ./infra/scripts/init-letsencrypt.sh edutrack.pe correo@dominio.pe
set -euo pipefail
DOMINIO="${1:?Uso: $0 <dominio> <email>}"
EMAIL="${2:?Uso: $0 <dominio> <email>}"
cd "$(dirname "$0")/.."

docker run --rm \
  -v "$PWD/certbot/conf:/etc/letsencrypt" \
  -v "$PWD/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d "$DOMINIO" -d "www.$DOMINIO" --email "$EMAIL" --agree-tos --no-eff-email

echo "Listo. Descomenta el bloque HTTPS en infra/nginx/default.conf y reinicia nginx."
