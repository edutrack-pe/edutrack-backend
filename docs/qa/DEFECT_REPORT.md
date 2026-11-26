# Reporte de defectos · MVP TB4

Severidad: **Alta** (incumple un criterio de aceptación o un RNF), **Media** (comportamiento incorrecto con alternativa), **Baja** (calidad o mantenimiento).

## Corregidos
| ID | Historia | Severidad | Descripción | Corrección | Verificación |
|---|---|---|---|---|---|
| D‑01 | HU01 | Alta | El token JWT vencía a los 120 min; el TB4 pide 8 h | `jwt_expires_minutes = 480` (`JWT_EXPIRES_MINUTES`) (BE `b6fe62e`) | `test_token_dura_8_horas_y_lleva_el_rol` |
| D‑02 | HU03 | Alta | La carga insertaba las filas válidas y omitía las erróneas (no transaccional) | Validación completa antes de insertar; un error → 0 filas | `test_un_error_detiene_toda_la_carga`, E2E Esc. 3 |
| D‑03 | HU03 | Alta | Se podían registrar notas duplicadas (estudiante, curso, bimestre) | Restricción única + verificación en la carga; migración Alembic (BE `bc48ac3`) | `test_reimportar_…`, `test_migraciones` |
| D‑04 | HU04 | Alta | Los «factores» eran la importancia global del modelo, iguales para todos | Explicación por oclusión individual | ML `test_predict.py` |
| D‑05 | HU04 | Alta | El entrenamiento no tenía VIF, SMOTE ni validación cruzada | Pipeline imblearn + VIF + GridSearchCV 5 folds (ML `3d65e99`) | ML `test_pipeline.py` |
| D‑06 | HU06 | Alta | Recalcular el riesgo duplicaba las alertas | Se registra una alerta por estudiante/periodo | `test_alertas_con_detalle_sin_duplicados_y_por_tutor` |
| D‑07 | HU02 | Media | `GET /notas` no devolvía el nombre del curso | *Join* con `Curso` | `test_corregir_nota_y_conducta` |
| D‑08 | HU02 | Media | Objeto expirado tras el *commit* de auditoría (error 500 al editar) | `refresh` después del *commit* | `test_registrar_editar_y_persistir_estudiante` |
| D‑09 | RNF‑01 | Alta | `POST /predicciones/aula` con p95 de 2,9 s | Oclusión en lote (ML `9fe94cd`) → p95 1,1 s | `PERFORMANCE_REPORT.md` |
| D‑10 | Seguridad | Alta | 60 vulnerabilidades conocidas en dependencias Python; 15 en npm | Actualización y fijado de versiones | `SECURITY_REPORT.md` |
| D‑11 | HU03 | Media | Sin límite de tamaño de archivo | Máximo 5 MB → 413 (BE `eabacc1`) | `test_archivo_demasiado_grande` |
| D‑12 | HU03 | Media | El mock del frontend aceptaba `.xls` y devolvía siempre «118 registros» | Contrato del mock alineado al backend | FE `gestion.test.tsx`, `datos.test.ts` |

## Abiertos
| ID | Área | Severidad | Descripción | Motivo / plan |
|---|---|---|---|---|
| O‑01 | HU04 / RNF‑02 | Alta | F1 en test = **0,740** (< 0,75). AUC 0,912 cumple | No se alteró el conjunto de prueba. El modelo se publicó con `--forzar` solo para la demo académica. Plan: más variables (asistencia por bimestre, historial), datos reales anonimizados, calibrar umbral. Ver `edutrack-ml/docs/ml/MODEL_EVALUATION.md`. |
| O‑02 | Seguridad | Media | Sin límite de intentos de login | Fuera del alcance de las HU; recomendado antes de producción |
| O‑03 | Seguridad | Baja | 9 hallazgos npm residuales (2 críticos solo de desarrollo) | Requieren versiones mayores |
| O‑04 | Seguridad | Media | Token en `localStorage` | Migrar a cookie `HttpOnly` |
| O‑05 | Despliegue | Alta | No hay evidencia de AWS EC2/RDS configurado | Requiere acceso a la cuenta; no se declara como hecho |
| O‑06 | HU03 | Baja | El TB4 asigna la carga masiva al **Analista**; por decisión del equipo solo el **Docente** carga notas | Actualizar el informe TB4 o revertir la regla |
| O‑07 | HU04 | Media | Modelo entrenado solo con datos sintéticos | Validar con datos reales anonimizados y con consentimiento |
