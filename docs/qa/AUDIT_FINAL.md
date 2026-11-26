# Auditoría final · MVP TB4

**Fecha:** 26/11/2026 · **Ramas auditadas:** `feature/mvp-tb4` en edutrack-backend, edutrack-frontend y edutrack-ml.
**Criterio:** una historia cuenta como «cumplida» solo si **todos** sus criterios de aceptación están verificados por pruebas automatizadas que pasan. Ver `TRACEABILITY_MATRIX.md`.

## 1. Estado por historia

| HU | Funcionalidad | Estado inicial (`AUDIT_INITIAL.md`) | Estado final | Evidencia |
|---|---|---|---|---|
| HU01 | Autenticación JWT + RBAC | Parcial (token de 120 min) | ✅ Cumplida | BE `test_mvp.py`, `test_auth_rbac.py`; FE `acceso.test.tsx`; E2E Esc. 1 |
| HU02 | Registro y edición de estudiantes | Parcial (sin alta/edición desde la UI) | ✅ Cumplida | BE `test_mvp.py`; FE `mvp.test.tsx`; E2E Esc. 2 |
| HU03 | Carga masiva CSV/XLSX | Parcial (no transaccional, duplicados) | ✅ Cumplida | BE `test_ingesta.py` (21); E2E Esc. 3 |
| HU04 | Predicción Random Forest | Parcial (sin VIF/SMOTE/CV, factores globales) | ⚠️ Funcional; **RNF‑02 no cumplido** (F1 0,740) | ML `test_pipeline.py`, `test_predict.py`; BE `test_mvp.py`; E2E Esc. 4a/4b |
| HU05 | Dashboard con filtros | Parcial (sin filtros) | ✅ Cumplida | BE `test_dashboard_*`; FE `mvp.test.tsx`; E2E Esc. 5 |
| HU06 | Alertas al tutor | Parcial (duplicadas) | ✅ Cumplida | BE `test_alertas_*`; FE `gestion.test.tsx`; E2E Esc. 6 |
| HU07 | Portal familiar | Parcial (sin aviso preventivo) | ✅ Cumplida | BE `test_portal_familiar_aislado`; FE; E2E Esc. 7 |

**Cumplimiento verificado: 6 de 7 historias (85,7 %).** HU04 implementa todos sus criterios funcionales, pero el modelo no alcanza la meta F1 ≥ 0,75 del RNF‑02, por lo que no se cuenta como cumplida.

## 2. Requisitos no funcionales y DoD

| Requisito | Meta | Resultado | Estado |
|---|---|---|---|
| RNF‑01 Rendimiento | p95 ≤ 2 s | p95 máx. 1,1 s (predicción de aula); agregado 650 ms; 0 fallos con 30 usuarios | ✅ local (ver `PERFORMANCE_REPORT.md`) |
| RNF‑02 Calidad del modelo | F1 ≥ 0,75 y AUC > 0,80 | F1 0,740 · AUC 0,912 (test, 400 filas) | ❌ F1 |
| Seguridad | JWT, RBAC, sin dependencias vulnerables | 0 vulnerabilidades Python; 9 npm residuales (2 críticas solo de desarrollo) | ⚠️ ver `SECURITY_REPORT.md` |
| Cobertura | > 70 % | BE 95 %, FE 99,81 %, ML 86 % | ✅ |
| E2E integral | Flujo completo sin mocks | 8/8 escenarios | ✅ |
| Migraciones | Esquema versionado | Alembic `0001`, verificado contra los modelos en SQLite y en **MySQL 8.4** | ✅ |
| Base de datos MySQL | Persistencia real | Suite del backend y E2E integral 8/8 sobre MySQL 8.4 local; TLSv1.3 hacia la base | ✅ local (ver `DATABASE_REPORT.md`) |
| Cifrado en reposo | Datos cifrados | Desactivado en la verificación local; RDS sin evidencia | ⚠️ O‑08 |
| Swagger | `/docs` disponible | Sí | ✅ |
| Despliegue AWS EC2/RDS | Operativo | **Sin evidencia**; existen `infra/` y `deploy.yml`, no verificados | ⚠️ no declarado |

## 3. Defectos
13 corregidos (D‑01…D‑13) y 8 abiertos (O‑01…O‑08). Detalle en `DEFECT_REPORT.md`.

## 4. Limitaciones de esta auditoría
- El informe TB4 se contrastó a partir de **extractos** (historias, criterios, RNF, DoD), no del documento completo.
- Todos los datos son sintéticos; no se usaron datos personales reales.
- El rendimiento se midió en un solo equipo con SQLite. La persistencia se verificó además en MySQL 8.4 local, no en RDS.
- No se tuvo acceso a la cuenta AWS; no se afirma que EC2/RDS estén configurados.
- Decisión del equipo: solo el **Docente** carga notas (el TB4 menciona al Analista) — O‑06.

## 5. Recomendación
Las ramas están listas para revisión por *pull request* (no se fusionaron con `main`). Antes de producción: resolver O‑01 (mejorar el modelo con datos reales anonimizados), O‑02 y O‑04 (endurecer autenticación) y documentar el despliegue real (O‑05).
