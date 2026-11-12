# ADR-001 · Tres repositorios (uno por componente desplegable)

- **Estado:** aceptado
- **Fecha:** 2026-11-12

## Contexto

EduTrack tiene tres componentes que se despliegan como contenedores independientes: la SPA React, la API de negocio (FastAPI) y el microservicio de predicción (FastAPI + scikit-learn). El equipo es de 5 personas con 10 h/semana durante 14 semanas.

## Decisión

Usar **tres repositorios** en la organización `edutrack-pe`:

| Repo | Contenido |
|---|---|
| `edutrack-frontend` | React + Vite + TypeScript |
| `edutrack-backend` | API FastAPI + `infra/` (Docker Compose, Nginx, deploy) + `docs/` |
| `edutrack-ml` | `ml-service/` (API de predicción) + `ml-research/` (notebooks) |

## Consecuencias

**A favor**
- Cada repo corresponde a un componente del diagrama de arquitectura: el desacoplamiento es explícito.
- CI independiente por componente (cobertura > 70 % en backend y ML).
- Permisos diferenciados (p. ej. `ml-research` con datos sensibles).

**En contra**
- Cambios que cruzan frontend y backend requieren 2 PR coordinados.
- El entorno local requiere clonar los 3 repos en la misma carpeta (`infra/docker-compose.yml` los referencia por ruta relativa).

**Mitigación:** el contrato entre componentes está documentado (OpenAPI en `/docs` y contrato de `/predict` en `edutrack-ml`), y cualquier cambio se anuncia en el PR.
