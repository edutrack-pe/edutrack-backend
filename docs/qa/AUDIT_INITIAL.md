# Auditoría inicial del MVP TB4

**Fecha:** 26/11/2026 · **Alcance:** `edutrack-backend`, `edutrack-frontend`, `edutrack-ml` (rama `main` antes de `feature/mvp-tb4`).
**Referencia:** informe TB4 (Tabla 39 *User Story Map*, Tabla 42 *Definition of Done*, fichas Gherkin de la Tabla 43).

> **Limitación de la fuente.** El archivo `.docx` del informe TB4 ya no estaba disponible durante la auditoría ni existe una versión PDF. Se trabajó con extractos textuales del informe (Tabla 39, Tabla 42, mensajes exactos de los escenarios Gherkin) y con el detalle de historias indicado por el equipo. Cualquier criterio del informe que no figure en esos extractos no pudo contrastarse.

## 1. Estado encontrado por historia (Must Have)

| HU | Funcionalidad | Estado inicial | Hallazgos |
|---|---|---|---|
| HU01 | Autenticación JWT y RBAC | Parcial | Login, hash bcrypt, `require_role` y 401/403 funcionaban. El token expiraba a los **120 min**; el TB4 pide sesión de **8 horas**. |
| HU02 | Registro y edición de estudiantes | Parcial | Existía `POST /estudiantes` con validación mínima. **No había edición** (`PUT`), ni validación de formato de código, ni normalización de nombres, ni vínculo con apoderado desde la interfaz. |
| HU03 | Carga masiva CSV/XLSX | Parcial | La carga **no era transaccional**: insertaba las filas válidas y descartaba las erróneas. **No detectaba duplicados** (ni en el archivo ni contra la base). El selector aceptaba `.xls`. No había límite de tamaño. |
| HU04 | Random Forest con SMOTE | No conforme | `scripts/train_dummy.py` entrenaba un RF simple **sin SMOTE, sin VIF, sin validación cruzada ni métricas** reportadas. Los "factores" eran el **mismo top‑3 global** para todos los estudiantes. Sin versión de modelo. |
| HU05 | Dashboard con semáforos | Parcial | Totales por nivel y por aula. **Sin filtros** por grado/sección, sin "evaluados" ni porcentajes, sin el mensaje de filtro vacío. |
| HU06 | Alertas para tutores | Parcial | Se creaba una alerta por cada estudiante en rojo en **cada recálculo (duplicados)**. Sin detalle (aula, probabilidad, factores) ni endpoint de detalle. |
| HU07 | Portal familiar | Parcial | Ficha con pautas y aislamiento del apoderado. Faltaba porcentaje de asistencia, conducta y un mensaje que presente el nivel como **señal preventiva** y no diagnóstico. |

## 2. Base de datos

- Sin migraciones: `alembic/versions` vacío; el esquema se creaba con `create_all`.
- Sin restricciones de unicidad en notas, asistencias ni conducta (permitía duplicados).
- `Prediccion` no guardaba la versión del modelo; `Alerta` no referenciaba la predicción que la originó.

## 3. Requisitos no funcionales

| RNF | Estado inicial |
|---|---|
| RNF-01 · p95 ≤ 2 s | **No medido** (no existían pruebas de carga). |
| RNF-02 · F1 ≥ 0,75 y AUC > 0,80 | **No medido**: el entrenamiento no reportaba métricas. |
| Seguridad | Sin revisión de dependencias. CORS restringido y bcrypt correctos. |
| Cobertura > 70 % | Backend y frontend la verificaban en CI; ML no tenía umbral. |

## 4. Pruebas existentes

- Backend: pytest con cliente FastAPI y ML simulado (≈30 pruebas).
- Frontend: Vitest + MSW, axe-core y Playwright **con backend simulado**. No había un E2E contra el stack real.
- ML: pruebas del endpoint `/predict` con el modelo *dummy*.

## 5. Despliegue

- Frontend publicado en Vercel en **modo demo** (`VITE_USE_MOCKS=true`).
- Rama `deploy` de backend y ML con *blueprints* de Render preparados; **no hay evidencia** de un despliegue en AWS EC2/RDS (el TB4 lo declara como arquitectura objetivo).

## 6. Decisión de alcance a señalar

El TB4 asigna la carga masiva al rol **analista**. Durante el proyecto, el equipo decidió (instrucción explícita del usuario) que **solo el docente registra y carga notas de sus propios cursos** y el resto de roles las consulta. La implementación sigue esa decisión; queda registrada como desviación respecto del informe (ver `DEFECT_REPORT.md`, O‑06).
