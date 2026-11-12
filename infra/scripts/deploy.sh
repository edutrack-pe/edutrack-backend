#!/usr/bin/env bash
# Despliegue en EC2. Estructura esperada en el servidor:
#   ~/edutrack/edutrack-backend   ~/edutrack/edutrack-ml   ~/edutrack/edutrack-frontend
# y el archivo ~/edutrack/edutrack-backend/.env con DATABASE_URL de RDS, JWT_SECRET, etc.
set -euo pipefail
BASE="${EDUTRACK_HOME:-$HOME/edutrack}"

for repo in edutrack-backend edutrack-ml edutrack-frontend; do
  echo ">> Actualizando $repo"
  git -C "$BASE/$repo" pull --ff-only
done

cd "$BASE/edutrack-backend"
docker compose -f infra/docker-compose.prod.yml --env-file .env up -d --build
docker image prune -f
docker compose -f infra/docker-compose.prod.yml ps
