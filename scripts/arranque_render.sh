#!/bin/sh
# Arranque en Render (plan gratuito): crea tablas, carga los datos demo si la base está vacía y levanta la API.
set -e

# Sin DATABASE_URL se usa SQLite dentro del contenedor (los datos vuelven a cero en cada reinicio).
if [ -z "$DATABASE_URL" ]; then
  unset DATABASE_URL
  echo "DATABASE_URL vacío: usando SQLite temporal con datos demo."
fi

python scripts/seed.py

# El servicio de ML también se duerme en el plan gratuito: se despierta en segundo plano
# para que el primer "Calcular riesgo" no espere el arranque en frío.
if [ -n "$ML_SERVICE_URL" ]; then
  python -c "import httpx, os; httpx.get(os.environ['ML_SERVICE_URL'].rstrip('/') + '/health', timeout=120)" >/dev/null 2>&1 &
fi

# Render termina HTTPS en su proxy: se confía en sus cabeceras X-Forwarded-*.
export FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-*}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
