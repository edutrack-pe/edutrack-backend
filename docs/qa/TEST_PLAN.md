# Plan de pruebas · MVP TB4

## 1. Objetivo
Verificar con evidencia automatizada que las historias Must Have (HU01–HU07) cumplen sus criterios de aceptación y que se alcanzan los requisitos no funcionales del TB4 (rendimiento, calidad del modelo, seguridad y cobertura).

## 2. Alcance
| Incluido | Excluido |
|---|---|
| Backend FastAPI, microservicio ML, frontend React | Historias Should/Could (Release 2) |
| Datos **sintéticos** (seed de demostración y dataset del modelo) | Datos personales reales |
| Entorno local y CI de GitHub Actions | Producción, AWS EC2/RDS (sin acceso ni evidencia) |

## 3. Niveles y herramientas

| Nivel | Herramienta | Repositorio | Qué valida |
|---|---|---|---|
| Unitarias / integración de API | pytest + TestClient + ML simulado | BE | Reglas de negocio, RBAC, validaciones, transacciones, migración |
| Unitarias del modelo | pytest | ML | Dataset, limpieza, VIF, métricas, *quality gate*, contrato `/predict` |
| Componentes y contrato | Vitest + Testing Library + MSW | FE | Pantallas por rol, estados de carga/vacío/error, formularios |
| Accesibilidad | axe-core (Vitest) y @axe-core/playwright | FE | WCAG 2.1 AA |
| E2E con backend simulado | Playwright (móvil, tablet, escritorio) | FE | Navegación por rol y flujos de UI |
| **E2E integral** | Playwright **contra el stack real** | FE | Flujo completo Auth → registro → carga → predicción RF → dashboard → alerta → portal |
| Rendimiento | Locust | BE | p50/p95/p99 de endpoints críticos con 30 usuarios |
| Seguridad | pip-audit, npm audit, revisión manual | todos | Dependencias vulnerables, secretos, controles de acceso |

## 4. Entorno del E2E integral y de rendimiento
- ML: `uvicorn app.main:app --port 8001` con el modelo entrenado por `python -m pipeline.entrenar`.
- Backend: `uvicorn app.main:app --port 8000` con **SQLite** nuevo y `python scripts/seed.py` (3 aulas, 90 estudiantes, 9 usuarios demo).
- Frontend: `vite --port 5173` con `VITE_USE_MOCKS=false` y `VITE_API_URL=http://localhost:8000/api`.
- La contraseña de los usuarios demo se genera al levantar el entorno (`SEED_DEFAULT_PASSWORD`) y se pasa a las pruebas por `E2E_PASSWORD` / `EDUTRACK_PASSWORD`; no se guarda en los repositorios.
- Equipo: Windows 11, Python 3.12, Node 24, un solo equipo para cliente y servidores (los resultados de rendimiento son **indicativos**, no de producción).

## 5. Criterios de entrada y salida
- **Entrada:** rama `feature/mvp-tb4` compila; seed y modelo disponibles.
- **Salida:** 0 pruebas fallidas; cobertura > 70 % en los tres repositorios; p95 ≤ 2 s en todos los endpoints medidos; 0 dependencias vulnerables en producción o riesgo residual documentado; métricas del modelo reportadas sin alterar el conjunto de prueba.

## 6. Ejecución
```bash
# Backend
pytest --cov=app --cov-fail-under=70
# ML
python -m pipeline.entrenar            # falla (exit 1) si F1 < 0,75 o AUC ≤ 0,80
pytest --cov=app --cov=pipeline --cov-fail-under=70
# Frontend
npm run lint && npm run test:coverage && npm run test:e2e && npm run build
E2E_PASSWORD=<clave> npx playwright test -c playwright.integral.config.ts
# Rendimiento (stack levantado)
EDUTRACK_PASSWORD=<clave> locust -f tests/performance/locustfile.py --headless -u 30 -r 5 -t 3m --host http://localhost:8000
```

## 7. Riesgos de la prueba
- Datos sintéticos: el desempeño del modelo puede diferir con datos reales.
- Rendimiento medido en un solo equipo con SQLite; en MySQL/RDS y red real los tiempos cambian.
- El informe TB4 solo se contrastó con extractos (ver `AUDIT_INITIAL.md`).
