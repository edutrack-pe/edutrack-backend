# Despliegue gratuito en Render (rama `deploy`)

La API y el servicio de ML se publican en Render con su plan gratuito. Cada repositorio tiene una rama
`deploy` con su `render.yaml`. Render solo publica cuando se actualiza esa rama, así que `main` sigue
siendo la rama de trabajo.

| Servicio | Repositorio | Archivo |
|---|---|---|
| `edutrack-ml` | `edutrack-ml` (carpeta `ml-service`) | `render.yaml` |
| `edutrack-api` | `edutrack-backend` | `render.yaml` + `scripts/arranque_render.sh` |
| Base de datos | MySQL gratis externo (Aiven o TiDB Cloud) | — |

## 1. Base de datos MySQL gratuita

Elige una de las dos y copia sus datos de conexión (host, puerto, usuario, clave y base).

- **Aiven** (aiven.io): crea un servicio *MySQL* en el plan *Free*. La base se llama `defaultdb`.
  URL para `DATABASE_URL`:
  `mysql+pymysql://USUARIO:CLAVE@HOST:PUERTO/defaultdb?ssl_check_hostname=false`
- **TiDB Cloud Serverless** (tidbcloud.com): crea un clúster *Serverless* y una base `edutrack`.
  URL para `DATABASE_URL`:
  `mysql+pymysql://USUARIO:CLAVE@HOST:4000/edutrack?ssl_ca=/etc/ssl/certs/ca-certificates.crt`

Si la clave tiene caracteres como `@`, `:` o `/`, escríbelos codificados (`@` → `%40`, `:` → `%3A`, `/` → `%2F`).
Las tablas y los datos demo se crean solos en el primer arranque.

## 2. Servicio de ML

1. Render → **New → Blueprint** → repositorio `edutrack-ml` → rama `deploy` → **Apply**.
2. Al terminar, copia su URL pública, por ejemplo `https://edutrack-ml.onrender.com`.
3. Comprueba `https://edutrack-ml.onrender.com/health` → `{"status":"ok","modelo_cargado":true}`.

## 3. API

1. Render → **New → Blueprint** → repositorio `edutrack-backend` → rama `deploy`.
2. Render pide los valores que no están en el archivo:
   - `DATABASE_URL`: la URL del paso 1 (vacía = SQLite temporal que se borra en cada reinicio).
   - `ML_SERVICE_URL`: la URL del paso 2.
   - `SEED_DEFAULT_PASSWORD`: la contraseña de los usuarios demo (mínimo 8 caracteres).
   - `JWT_SECRET` se genera solo.
3. **Apply** y espera el primer despliegue.
4. Comprueba `https://edutrack-api.onrender.com/health` y la documentación en `/docs`.

## 4. Publicar cambios

```bash
git switch deploy
git merge main
git push origin deploy
```

## Límites del plan gratuito

- Cada servicio se duerme tras 15 minutos sin uso; la siguiente petición tarda de 30 a 60 segundos.
  Al despertar, la API despierta también al servicio de ML.
- 512 MB de RAM por servicio y sin disco persistente: los datos viven en la base MySQL externa.
- `CORS_ORIGINS` ya permite la demo de Vercel (`https://edutrack-frontend-theta.vercel.app`).
  Si el frontend se publica en otra URL, agrégala ahí separada por comas.
