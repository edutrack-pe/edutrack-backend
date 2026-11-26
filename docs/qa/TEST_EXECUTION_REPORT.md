# Reporte de ejecución de pruebas · MVP TB4

**Fecha de ejecución:** 26/11/2026 · **Ramas:** `feature/mvp-tb4` (backend, frontend, ml) · **Entorno:** Windows 11, Python 3.12.10, Node 24.

## Resumen

| Suite | Herramienta | Pruebas | Resultado |
|---|---|---|---|
| Backend (API, RBAC, ingesta, migración) sobre SQLite | pytest | 71 | ✅ 70 pasan · 1 omitida (requiere MySQL real) |
| Backend sobre **MySQL 8.4** (misma suite + TLS real) | pytest | 71 | ✅ 71 pasan |
| E2E integral con backend sobre **MySQL + TLS** | Playwright | 8 escenarios | ✅ 8 pasan |
| ML (pipeline y `/predict`) | pytest | 15 | ✅ 15 pasan |
| Frontend unitarias y de componentes | Vitest + MSW | 214 | ✅ 214 pasan |
| Frontend E2E con backend simulado (3 viewports) | Playwright | 74 | ✅ 74 pasan |
| **E2E integral contra el stack real** | Playwright | 8 escenarios | ✅ 8 pasan |
| Rendimiento (30 usuarios, 3 min) | Locust | 2 587 peticiones | ✅ 0 fallos; p95 máx. 1,1 s |
| Calidad del modelo (RNF‑02) | `pipeline.entrenar` | 1 | ❌ F1 0,740 < 0,75 (AUC 0,912 cumple) |

## Backend por archivo
| Archivo | Pruebas |
|---|---|
| `tests/test_mvp.py` (criterios HU01, HU02, HU04–HU07) | 25 |
| `tests/test_ingesta.py` (HU03) | 21 |
| `tests/test_auth_rbac.py` | 8 |
| `tests/test_academico.py` | 6 |
| `tests/test_flujo_riesgo.py` | 5 |
| `tests/test_ejemplos_carga.py` (archivos de `docs/ejemplos-carga`) | 1 |
| `tests/test_migraciones.py` (upgrade = modelos, downgrade) | 1 |
| `tests/test_db.py` (argumentos de conexión y TLS contra MySQL real) | 4 (1 solo con MySQL) |

## E2E integral (stack real, sin mocks)

Configuración: `edutrack-frontend/playwright.integral.config.ts`. Servicios: ML (8001) con el modelo `rf-20261126-9ad6a250`, backend (8000) con SQLite recién creado y seed, frontend Vite (5173). Reporte HTML, trazas y capturas en `playwright-report-integral/` y `test-results-integral/` (no versionados); capturas clave copiadas en `docs/qa/evidencias/e2e-integral/` y resumen en `resumen.json`.

| Escenario | Historia | Duración | Resultado | Evidencia |
|---|---|---|---|---|
| 1 · Autenticación, sesión y control de acceso | HU01 | ≈3 s | ✅ | `hu01-*.png` |
| 2 · Registrar, editar y persistir un estudiante | HU02 | ≈6 s | ✅ | `hu02-*.png` |
| 4a · Sin notas del bimestre no se predice | HU04 | <1 s | ✅ | `resumen.json` |
| 3 · Carga transaccional de notas (CSV) | HU03 | ≈6 s | ✅ | `hu03-*.png` |
| 4b · Predicción con el Random Forest real | HU04 | ≈4 s | ✅ | `hu04-calculo-aula.png` |
| 5 · Dashboard consistente con filtros | HU05 | ≈4 s | ✅ | `hu05-*.png` |
| 6 · Alertas al tutor del aula, sin fugas | HU06 | ≈4 s | ✅ | `hu06-*.png` |
| 7 · Portal familiar con recomendaciones y aislamiento | HU07 | ≈3 s | ✅ | `hu07-portal-familiar.png` |

**Resultados observados con el modelo real (no simulados):**
- Cálculo de 3° A, bimestre 1: **31 estudiantes evaluados**, 5 en riesgo alto, 4 moderado, 22 bajo; **5 alertas nuevas** para el tutor de 3° A.
- Estudiante sintético creado en la prueba (notas 5–8): riesgo **moderado**, probabilidad **0,6561** (bajo el umbral de 0,70), factores `promedio` y `cursos_desaprobados`.
- Tutor de 3° B no recibe alertas de 3° A; el apoderado `padre@` recibe 403 al pedir la ficha del estudiante de `padre2@`.

## Incidencias durante la ejecución
Las fallas encontradas y su corrección se registran en `DEFECT_REPORT.md`. Las corridas finales indicadas arriba se hicieron **después** de todas las correcciones, sobre bases de datos nuevas.

## Cómo reproducir
Ver `TEST_PLAN.md` §6.
