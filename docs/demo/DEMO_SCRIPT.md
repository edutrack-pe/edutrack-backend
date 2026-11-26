# Guion de demostración (≈ 10 minutos)

Recorre las siete historias Must Have en el mismo orden que el E2E integral. Requiere el stack levantado (ver `docs/architecture/DEPLOYMENT.md`) con seed recién cargado. Cuentas en `DEMO_ACCOUNTS.md`.

Archivos de apoyo: `docs/ejemplos-carga/` (`notas_validas.csv`, `notas_validas.xlsx`, `notas_error_fila_12.csv`, `notas_duplicadas.csv`, `notas_no_permitido.docx`).

## 1 · Acceso seguro (HU01) — 1 min
1. Ingresar con `director@edutrack.pe` y una contraseña incorrecta → «Credenciales incorrectas».
2. Ingresar correctamente → panorama del colegio.
3. Cerrar sesión, ingresar como `docente1@` → el menú solo muestra sus opciones; abrir `/alertas` en la barra de direcciones → redirige.
> Mensaje: la sesión dura 8 h y cada rol ve solo lo que le corresponde.

## 2 · Registro de estudiante (HU02) — 1,5 min
1. Como director: **Estudiantes → Registrar estudiante** (código nuevo, nombres, 3° A, apoderado).
2. Intentar registrar el mismo código → «Ya existe un estudiante con ese código».
3. Abrir la ficha → **Editar datos** → cambiar el apoderado → recargar: el cambio persiste.

## 3 · Carga masiva (HU03) — 2 min
1. Como `docente1@`: **Operaciones → Cargar notas**.
2. Subir `notas_no_permitido.docx` → «Formato no permitido, adjunte un archivo CSV o XLSX».
3. Subir `notas_error_fila_12.csv` → «Error en la fila 12: formato de nota inválido» y «No se importó ningún registro».
4. Subir `notas_validas.csv` → filas importadas. Volver a subirlo → error de duplicado, 0 insertados.

## 4 · Predicción (HU04) — 2 min
1. Como director, en la ficha del estudiante recién creado (sin notas) → **Calcular riesgo** → «Datos insuficientes…».
2. Panorama → **Calcular riesgo** del aula 3° A → resumen de evaluados, niveles y alertas nuevas.
3. Abrir un estudiante en rojo: probabilidad, **factores propios** del estudiante y versión del modelo `rf-…`.
> Transparencia: el modelo usa datos sintéticos; AUC 0,91 y F1 0,74 (meta 0,75 no alcanzada). Es una señal preventiva, no un diagnóstico.

## 5 · Dashboard (HU05) — 1 min
1. Filtrar grado 3, sección B → solo 3° B. Filtrar por riesgo alto → la lista coincide con el contador.
2. Elegir un filtro sin datos → «Sin información disponible para el filtro seleccionado».

## 6 · Alertas (HU06) — 1 min
1. Como `tutor1@`: **Alertas** → una por estudiante en rojo de 3° A, con factores. Marcar una como leída → el contador baja.
2. Como `tutor2@`: no ve las alertas de 3° A.

## 7 · Portal familiar (HU07) — 1 min
1. Como `padre@`: ve solo a su hijo(a), con notas, asistencia, nivel y recomendaciones para el hogar; sin probabilidades numéricas; aviso «señal preventiva, no un diagnóstico».

## Cierre — 30 s
Pruebas: 67 backend, 15 ML, 214 frontend, 74 E2E con mocks y 8 E2E integrales; cobertura > 85 % en los tres repositorios; p95 ≤ 1,1 s. Pendientes: F1 del modelo, límite de intentos de login y despliegue en AWS.
