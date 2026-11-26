# Reporte de rendimiento · RNF‑01 (p95 ≤ 2 s)

## Condiciones
| Elemento | Valor |
|---|---|
| Herramienta | Locust 2.32.4, modo *headless* |
| Script | `tests/performance/locustfile.py` (usuarios Director, Tutor, Analista y Padre con pesos realistas) |
| Carga | 30 usuarios concurrentes, rampa de 5 usuarios/s, 3 minutos |
| Stack | Backend FastAPI (uvicorn, 1 *worker*) + SQLite con seed; ML con el modelo `rf-20261126-9ad6a250`; todo en el mismo equipo |
| Equipo | Windows 11, Python 3.12 |
| Evidencia | `docs/qa/evidencias/rendimiento/{antes,despues}-optimizacion/locust_stats.csv` y `locust.html` |

> Los resultados son **indicativos**: un solo equipo genera la carga y atiende las peticiones, sin red real ni MySQL/RDS. No equivalen a una medición en producción.

## Resultado final (después de la optimización)
2 587 peticiones, **0 fallos**. Tiempos en milisegundos.

| Endpoint | p50 | p95 | p99 | ¿p95 ≤ 2 000 ms? |
|---|---|---|---|---|
| GET /alertas | 19 | 64 | 110 | ✅ |
| GET /dashboard/resumen | 14 | 52 | 98 | ✅ |
| GET /dashboard/resumen?grado | 12 | 35 | 55 | ✅ |
| GET /estudiantes | 15 | 69 | 110 | ✅ |
| GET /estudiantes/{id} (ficha) | 21 | 62 | 99 | ✅ |
| GET ficha (padre) | 21 | 59 | 84 | ✅ |
| POST /auth/login (bcrypt) | 400 | 420 | 420 | ✅ |
| POST /predicciones/aula | 850 | 1 100 | 1 200 | ✅ |
| POST /predicciones/estudiante | 590 | 790 | 950 | ✅ |
| **Agregado** | **20** | **650** | **900** | ✅ |

## Hallazgo y optimización (D‑09)
En la primera corrida, **POST /predicciones/aula** tenía p50 1 900 ms, **p95 2 900 ms** y p99 3 200 ms: incumplía RNF‑01.

**Causa:** la explicación por oclusión llamaba a `predict_proba` una vez por estudiante y por variable (≈ 31 × 7 llamadas por aula).
**Corrección (ML `9fe94cd`):** `RiskModel.factores_lote` arma todas las variantes ocluidas en una sola matriz y hace **una** llamada a `predict_proba`. Las salidas son idénticas antes y después (verificado por prueba); un aula de 31 estudiantes pasó de 1,65 s a 0,22 s en el microservicio.

| POST /predicciones/aula | p50 | p95 | p99 |
|---|---|---|---|
| Antes | 1 900 | 2 900 | 3 200 |
| Después | 850 | 1 100 | 1 200 |

## Observaciones
- El login tarda ≈ 400 ms por el costo de bcrypt; es intencional (resistencia a fuerza bruta).
- La predicción del aula es el endpoint más pesado; con más estudiantes por aula o en un servidor con menos CPU podría acercarse al límite. Se recomienda volver a medir en el entorno de despliegue.

## Cómo reproducir
```bash
# con el stack levantado (ver TEST_PLAN.md §4)
EDUTRACK_PASSWORD=<clave> locust -f tests/performance/locustfile.py --headless -u 30 -r 5 -t 3m \
  --host http://localhost:8000 --csv reports/locust --html reports/locust.html
```
