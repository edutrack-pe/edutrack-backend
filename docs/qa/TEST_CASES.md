# Casos de prueba · MVP TB4

Casos representativos por historia. Cada caso está automatizado; la columna **Prueba** indica dónde.
Datos: usuarios y estudiantes **sintéticos** del seed (`director@`, `analista@`, `docente1@`, `docente2@`, `tutor1@` (3° A), `tutor2@` (3° B), `padre@`, `padre2@` `edutrack.pe`).

## HU01 · Autenticación y control de acceso

| ID | Precondición | Pasos | Resultado esperado | Prueba |
|---|---|---|---|---|
| CP-01 | Usuario activo | Login con contraseña incorrecta | 401 «Credenciales incorrectas»; no se emite token | BE `test_mvp.py`, E2E Esc. 1 |
| CP-02 | — | Login correcto como tutor | Token HS256 con `rol=tutor` y vencimiento de 8 h | BE `test_token_dura_8_horas_y_lleva_el_rol` |
| CP-03 | — | `GET /estudiantes` sin token, con token vencido o firmado con otra clave | 401 | BE `test_sin_token_401`, `test_token_vencido_o_alterado_401` |
| CP-04 | Docente autenticado | `PUT /config/riesgo`, `GET /alertas` | 403 | BE `test_rol_sin_permiso_403`, E2E Esc. 1 |
| CP-05 | Cada rol | Abrir el menú y rutas no permitidas | Solo ve sus opciones; rutas ajenas redirigen | FE `acceso.test.tsx`, `e2e/roles.spec.ts` |

## HU02 · Registro y edición de estudiantes

| ID | Precondición | Pasos | Resultado esperado | Prueba |
|---|---|---|---|---|
| CP-06 | Director | Registrar código « b0101 », nombres con espacios extra | 201; código `B0101`, nombres normalizados | BE `test_registrar_editar_y_persistir_estudiante`, FE `mvp.test.tsx`, E2E Esc. 2 |
| CP-07 | Director | Registrar con código existente | 409 «Ya existe un estudiante con ese código» | BE, FE `mvp.test.tsx`, E2E Esc. 2 |
| CP-08 | Director | Código `123`, nombres vacíos, aula 9999, apoderado que no es padre | 422 / 422 / 404 / 422 | BE `test_validaciones_de_registro` |
| CP-09 | Director | Editar aula y apoderado; leer con analista | Cambios persistidos; el nuevo apoderado ve al estudiante | BE, E2E Esc. 2 (recarga) |
| CP-10 | Tutor 3° A | Corregir nombre; intentar cambiar aula o editar a un estudiante de otra aula | 200 / 403 / 403 | BE `test_permisos_de_edicion`, FE `mvp.test.tsx` |
| CP-11 | Docente1 | Corregir nota propia; docente2 corrige la misma | 200 / 403; rango 0–20 validado | BE `test_corregir_nota_y_conducta` |

## HU03 · Carga masiva

| ID | Precondición | Pasos | Resultado esperado | Prueba |
|---|---|---|---|---|
| CP-12 | Docente1 | Subir CSV válido y XLSX válido | Todas las filas insertadas; consultables | BE `test_ingesta.py`, E2E Esc. 3 |
| CP-13 | Docente1 | CSV con «quince» en la fila 12 | «Error en la fila 12: formato de nota inválido»; **0 insertados** | BE `test_un_error_detiene_toda_la_carga`, E2E Esc. 3 |
| CP-14 | Docente1 | Subir `.docx`, `.pdf`, `.xls`, sin extensión | 400 «Formato no permitido, adjunte un archivo CSV o XLSX»; la UI lo bloquea antes de enviar | BE `test_formato_no_permitido`, FE `gestion.test.tsx`, E2E Esc. 3 |
| CP-15 | Docente1 | Registro repetido en el archivo / reimportar | Error de duplicado con fila; 0 insertados | BE `test_duplicado_dentro_del_archivo`, `test_reimportar_…` |
| CP-16 | Docente1 | Curso inexistente, curso de otro docente, nota 25, bimestre 9, fecha futura | Error por fila con mensaje específico | BE `test_validaciones_por_fila`, `test_asistencias` |
| CP-17 | Director, analista, tutor, padre | Subir CSV | 403 (solo el docente carga) | BE `test_solo_el_docente_importa` |
| CP-18 | Docente1 | Archivo de más de 5 MB | 413 | BE `test_archivo_demasiado_grande` |

## HU04 · Predicción con Random Forest

| ID | Precondición | Pasos | Resultado esperado | Prueba |
|---|---|---|---|---|
| CP-19 | Dataset sintético | `python -m pipeline.entrenar` | VIF, SMOTE dentro del pipeline, CV 5 folds, métricas en `reports/metricas.json`; exit 1 si no cumple RNF‑02 | ML `test_pipeline.py` |
| CP-20 | Estudiante sin notas del bimestre | Predecir | 422 «Datos insuficientes: registre las calificaciones del bimestre actual»; **no se llama al ML** | BE `test_datos_insuficientes_no_llama_al_ml`, E2E Esc. 4a |
| CP-21 | Notas cargadas | Predecir aula con el RF real | Predicción guardada con versión `rf-AAAAMMDD-hash` y fecha | BE, E2E Esc. 4b |
| CP-22 | — | Bajar las notas del estudiante y repetir | La probabilidad sube | BE `test_la_prediccion_cambia_si_cambian_los_datos` |
| CP-23 | — | Predecir estudiantes con distinto perfil | Factores individuales distintos | ML `test_predict.py` |

## HU05 · Dashboard

| ID | Precondición | Pasos | Resultado esperado | Prueba |
|---|---|---|---|---|
| CP-24 | 3° A calculado | Consultar resumen | verde+amarillo+rojo = evaluados; porcentajes suman 100; coincide con lista filtrada por riesgo | BE `test_dashboard_consistente_y_filtros`, E2E Esc. 5 |
| CP-25 | — | Filtrar grado 3 y sección B | Solo «3° B»; filtros enviados a la API | BE, FE `mvp.test.tsx`, E2E Esc. 5 |
| CP-26 | — | Filtro sin datos | «Sin información disponible para el filtro seleccionado» | FE `mvp.test.tsx` |
| CP-27 | Tutor1 | Abrir panorama | Solo su aula | BE `test_tutor_solo_ve_su_aula_en_el_dashboard` |

## HU06 · Alertas

| ID | Precondición | Pasos | Resultado esperado | Prueba |
|---|---|---|---|---|
| CP-28 | Estudiantes en riesgo alto en 3° A | Calcular riesgo | Una alerta por estudiante en rojo para tutor1, con aula, probabilidad y factores | BE `test_alertas_con_detalle_…`, E2E Esc. 6 |
| CP-29 | — | Recalcular | `alertas_generadas = 0`; no se duplican | BE |
| CP-30 | Tutor2 | Listar / abrir / marcar la alerta de 3° A | Lista vacía; 404 al abrirla o marcarla | BE, E2E Esc. 6 |
| CP-31 | Tutor1 | Marcar como leída | El contador de no leídas baja en 1 y persiste | BE, FE `gestion.test.tsx`, E2E Esc. 6 |

## HU07 · Portal familiar

| ID | Precondición | Pasos | Resultado esperado | Prueba |
|---|---|---|---|---|
| CP-32 | padre / padre2 | Listar estudiantes | Cada uno solo ve a su hijo(a) | BE `test_portal_familiar_aislado` |
| CP-33 | Padre | Abrir la ficha del hijo | Notas, asistencia %, nivel, recomendaciones; sin probabilidad numérica; aviso «señal preventiva, no un diagnóstico» | FE `mvp.test.tsx`, `seguimiento.test.tsx`, E2E Esc. 7 |
| CP-34 | Padre | Pedir ficha, notas, asistencias o predicciones de otro estudiante | 403 | BE, E2E Esc. 7 |
| CP-35 | — | Revisar textos de pautas | Sin términos estigmatizantes | BE `test_pautas_sin_lenguaje_estigmatizante` |
