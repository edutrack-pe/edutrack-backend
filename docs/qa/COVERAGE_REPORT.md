# Reporte de cobertura · MVP TB4

DoD del TB4 (Tabla 42, criterio 1): cobertura de pruebas unitarias **superior al 70 %** en backend y frontend. Se extiende al microservicio ML.

| Repositorio | Herramienta | Líneas | Ramas | Umbral en CI | Resultado |
|---|---|---|---|---|---|
| edutrack-backend | pytest-cov | **95 %** (1 123 sentencias, 52 sin cubrir) | — | `--cov-fail-under=70` | ✅ |
| edutrack-frontend | Vitest + V8 | **99,81 %** | **93,93 %** (funciones 96,48 %) | 80 % líneas/ramas/funciones | ✅ |
| edutrack-ml | pytest-cov | **86 %** (229 sentencias, 33 sin cubrir) | — | `--cov-fail-under=70` (nuevo) | ✅ |

## Backend: módulos con menor cobertura
| Módulo | Cobertura | Motivo |
|---|---|---|
| `app/services/ml_client.py` | 31 % | En las pruebas se reemplaza por un ML simulado; el cliente HTTP real se ejercita en el E2E integral y en Locust. |
| `app/db.py` | 50 % | Rama de configuración para MySQL (no se usa en pruebas con SQLite). |
| `app/services/ingesta.py` | 90 % | Ramas de errores de lectura poco frecuentes. |

## Frontend
Excluidos por configuración: `main.tsx`, tipos y archivos de prueba. Todas las páginas y componentes superan el 90 % de líneas.

## Cómo regenerar
```bash
pytest --cov=app --cov-report=html                    # backend → htmlcov/
pytest --cov=app --cov=pipeline --cov-report=html     # ml-service
npm run test:coverage                                 # frontend → coverage/
```
Los reportes HTML no se versionan (están en `.gitignore`); CI los recalcula en cada *push*.
