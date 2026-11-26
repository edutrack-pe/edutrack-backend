# Despliegue · EduTrack MVP TB4

## Estado real (26/11/2026)
| Entorno | Estado | Evidencia |
|---|---|---|
| Local (3 servicios + SQLite) | ✅ Verificado | E2E integral 8/8 y Locust (`docs/qa/`) |
| Frontend demo en Vercel | ✅ Publicado con **datos simulados** (`VITE_USE_MOCKS=true`); no se conecta a un backend | Proyecto Vercel del equipo |
| Backend + ML en Render (plan gratuito) | ⚠️ Preparado en las ramas `deploy` (`render.yaml`); no verificado como operativo desde esta auditoría | Ramas `deploy` |
| AWS EC2 + RDS (arquitectura objetivo del TB4) | ❌ **Sin evidencia** de configuración; existen `infra/` y `.github/workflows/deploy.yml` sin ejecución verificada | — |

> No se afirma que AWS esté configurado. Para declararlo se requiere: instancia EC2 en ejecución, RDS MySQL accesible solo desde la VPC, TLS y una ejecución exitosa de `deploy.yml`.

## Variables de entorno
| Servicio | Variable | Descripción |
|---|---|---|
| backend | `DATABASE_URL` | `mysql+pymysql://…` (producción) o `sqlite:///…` |
| backend | `JWT_SECRET` | **Obligatoria en producción**; secreto largo y aleatorio |
| backend | `JWT_EXPIRES_MINUTES` | 480 (8 h) |
| backend | `ML_SERVICE_URL` | URL interna de ml-service |
| backend | `CORS_ORIGINS` | Origen del frontend |
| backend | `SEED_DEFAULT_PASSWORD` | Solo para cargar la demo; nunca en el repositorio |
| frontend | `VITE_API_URL`, `VITE_USE_MOCKS` | URL del backend; `false` para usar la API real |
| ml | `MODEL_PATH` | Ruta del `model.joblib` |

## Pasos (cualquier entorno)
1. **ML:** `pip install -r requirements.txt` → `python -m pipeline.entrenar` (falla si no cumple RNF‑02; `--forzar` solo para demo) → `uvicorn app.main:app --port 8001`.
2. **Backend:** `pip install -r requirements.txt` → `alembic upgrade head` → (demo) `python scripts/seed.py` → `uvicorn app.main:app --port 8000`.
3. **Frontend:** `npm ci` → `npm run build` → servir `dist/` (Nginx/Vercel) con `VITE_API_URL` apuntando al backend.
4. **Verificar:** `GET /health` en backend y ML; login; ejecutar `playwright.integral.config.ts` contra el entorno.

## Antes de producción
- Fallar al arrancar si falta `JWT_SECRET` (hoy usa un valor de desarrollo).
- Límite de intentos de login; desactivar `/docs` públicos.
- Volver a medir RNF‑01 en el servidor real.
- No publicar el modelo con `--forzar` (O‑01).
