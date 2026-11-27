# Matriz de trazabilidad · MVP TB4

Relaciona cada historia y criterio con el código que lo implementa y la prueba automatizada que lo verifica.
Rutas relativas a cada repositorio (rama `feature/mvp-tb4`). **BE** = edutrack-backend · **FE** = edutrack-frontend · **ML** = edutrack-ml.

| HU | Criterio / escenario | Implementación | Prueba automatizada | Resultado |
|---|---|---|---|---|
| HU01 | Credenciales incorrectas → «Credenciales incorrectas», sin token | BE `app/routers/auth.py` | BE `tests/test_mvp.py::test_credenciales_incorrectas_no_generan_token` · FE `e2e-integral` Esc. 1 | ✅ |
| HU01 | Token JWT de 8 h con rol | BE `app/core/config.py`, `app/core/security.py` | BE `test_token_dura_8_horas_y_lleva_el_rol` | ✅ |
| HU01 | 401 sin token, vencido o alterado | BE `security.get_current_user` | BE `test_sin_token_401`, `test_token_vencido_o_alterado_401` · E2E Esc. 1 | ✅ |
| HU01 | 403 por rol sin permiso | BE `require_role` | BE `test_rol_sin_permiso_403`, `tests/test_auth_rbac.py` · E2E Esc. 1 | ✅ |
| HU01 | Menú y rutas por rol | FE `src/components/menu.tsx`, `ProtectedRoute` | FE `src/pages/acceso.test.tsx`, `e2e/roles.spec.ts` | ✅ |
| HU02 | Registrar estudiante con validaciones (código, nombres, aula, apoderado) | BE `app/routers/estudiantes.py`, `app/schemas` · FE `FormularioEstudiante.tsx` | BE `test_registrar_editar_y_persistir_estudiante`, `test_validaciones_de_registro` · FE `mvp.test.tsx` · E2E Esc. 2 | ✅ |
| HU02 | Duplicado de código → 409 | BE `crear_estudiante` | BE `test_validaciones_de_registro[409]` · FE `mvp.test.tsx` · E2E Esc. 2 | ✅ |
| HU02 | Editar y persistir (otra sesión lee el cambio) | BE `PUT /estudiantes/{id}` | BE `test_registrar_editar_y_persistir_estudiante` · E2E Esc. 2 (recarga) | ✅ |
| HU02 | Tutor solo corrige nombres; docente/apoderado no editan | BE `editar_estudiante` · FE formulario | BE `test_permisos_de_edicion` · FE `mvp.test.tsx` | ✅ |
| HU02 | Corrección de notas (docente del curso) y conducta | BE `PUT /notas/{id}`, `PUT /conducta` | BE `test_corregir_nota_y_conducta` | ✅ |
| HU03 | CSV y XLSX válidos se importan | BE `app/services/ingesta.py` | BE `tests/test_ingesta.py` (CSV, XLSX) · E2E Esc. 3 | ✅ |
| HU03 | «Error en la fila 12: formato de nota inválido» y no se inserta nada | BE `importar` (transaccional) | BE `test_un_error_detiene_toda_la_carga`, `test_ejemplos_de_carga` · FE `gestion.test.tsx` · E2E Esc. 3 | ✅ |
| HU03 | «Formato no permitido, adjunte un archivo CSV o XLSX» | BE `leer_archivo` · FE `formatoPermitido` | BE `test_formato_no_permitido` (docx, pdf, xls) · FE `gestion.test.tsx` · E2E Esc. 3 | ✅ |
| HU03 | Duplicados en el archivo y contra la base | BE `importar` + `uq_nota_estudiante_curso_bimestre` | BE `test_duplicado_dentro_del_archivo`, `test_reimportar_el_mismo_archivo_no_duplica` · E2E Esc. 3 | ✅ |
| HU03 | Plantilla y validaciones por fila (rango, curso, bimestre, fecha) | BE `ingesta.py` | BE `test_validaciones_por_fila`, `test_asistencias` | ✅ |
| HU03 | Archivo > 5 MB → 413 | BE `academico.ingesta` | BE `test_archivo_demasiado_grande` | ✅ |
| HU04 | Pipeline: limpieza, VIF, SMOTE solo en entrenamiento, CV 5 folds, métricas | ML `pipeline/entrenar.py` | ML `tests/test_pipeline.py` | ✅ |
| HU04 | Probabilidad ≥ 0,70 → riesgo alto | ML `RiskModel._nivel`, BE `ConfigRiesgo` | ML `tests/test_predict.py` · BE `tests/test_flujo_riesgo.py` | ✅ |
| HU04 | Factores individuales (no globales) | ML `RiskModel.factores_lote` (oclusión) | ML `test_predict.py` (factores distintos por estudiante) | ✅ |
| HU04 | Sin notas del bimestre → «Datos insuficientes…» sin llamar al ML | BE `app/services/prediccion.py` | BE `test_datos_insuficientes_no_llama_al_ml` · E2E Esc. 4a | ✅ |
| HU04 | Se guarda predicción con versión y fecha | BE `Prediccion.modelo_version` | BE `test_prediccion_individual_guarda_version_y_fecha` · E2E Esc. 4b | ✅ |
| HU04 | La predicción depende de los datos reales | BE + ML | BE `test_la_prediccion_cambia_si_cambian_los_datos` · E2E Esc. 4b (RF real) | ✅ |
| HU04 | RNF‑02: F1 ≥ 0,75 y AUC > 0,80 | ML `reports/metricas.json` | ML *quality gate* en CI | ✅ F1 0,755 · ✅ AUC 0,923 (CV F1 0,748 ± 0,019) |
| HU05 | Totales, evaluados, niveles y porcentajes consistentes | BE `GET /dashboard/resumen` | BE `test_dashboard_consistente_y_filtros` · E2E Esc. 5 | ✅ |
| HU05 | Filtros por grado, sección y riesgo | BE dashboard y `GET /estudiantes` · FE `FiltrosPanorama.tsx` | BE `test_dashboard_consistente_y_filtros` · FE `mvp.test.tsx` · E2E Esc. 5 | ✅ |
| HU05 | «Sin información disponible para el filtro seleccionado» | FE `Dashboard.tsx` | FE `mvp.test.tsx` | ✅ |
| HU05 | Estados de carga, vacío y error | FE `Cargando`, `Vacio`, `ErrorApi` | FE `seguimiento.test.tsx` | ✅ |
| HU06 | Alerta automática al tutor del aula con detalle y factores | BE `_registrar_alerta`, `GET /alertas/{id}` · FE `Alertas` | BE `test_alertas_con_detalle_sin_duplicados_y_por_tutor` · FE `gestion.test.tsx` · E2E Esc. 6 | ✅ |
| HU06 | Sin duplicados al recalcular | BE `_registrar_alerta` | BE (misma prueba) · FE `datos.test.ts` | ✅ |
| HU06 | Otro tutor no ve ni abre la alerta (Escenario 02) | BE `acceso.py` | BE (misma prueba) · E2E Esc. 6 | ✅ |
| HU06 | Marcar «Leída» reduce el contador en 1 (Escenario 03) | BE `PATCH /alertas/{id}/leer` · FE contador | BE (misma prueba) · FE `gestion.test.tsx` · E2E Esc. 6 | ✅ |
| HU07 | Portal con notas, asistencia, nivel y recomendaciones | BE ficha · FE `PortalPadre.tsx`, `DetalleFicha` | BE `test_portal_familiar_aislado` · FE `mvp.test.tsx` · E2E Esc. 7 | ✅ |
| HU07 | Lenguaje no estigmatizante; sin probabilidades para la familia | BE `app/services/pautas.py` · FE aviso preventivo | BE `test_pautas_sin_lenguaje_estigmatizante` · FE `seguimiento.test.tsx` · E2E Esc. 7 | ✅ |
| HU07 | Un apoderado no accede a otro estudiante | BE `obtener_estudiante` | BE `test_portal_familiar_aislado` · E2E Esc. 7 | ✅ |
| DoD | Cobertura > 70 % | CI de los tres repos | Ver `COVERAGE_REPORT.md` | ✅ 95 % / 99,8 % / 86 % |
| DoD | p95 ≤ 2 s | — | `tests/performance/locustfile.py` · `PERFORMANCE_REPORT.md` | ✅ (entorno local) |
| DoD | Documentación Swagger | FastAPI `/docs` | Verificación manual de `/docs` | ✅ |
| DoD | Persistencia en MySQL 8 y TLS hacia la base | BE `app/db.py`, `alembic/` | Suite BE con `TEST_DATABASE_URL`, `tests/test_db.py`, E2E integral sobre MySQL · `DATABASE_REPORT.md` | ✅ (local) |
| DoD | Despliegue en AWS EC2/RDS | `infra/`, `deploy.yml` | — | ⚠️ Sin evidencia |
