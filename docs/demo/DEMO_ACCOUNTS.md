# Cuentas de demostración

Cuentas **ficticias** creadas por `python scripts/seed.py` (datos en `app/seed_data.py`). No corresponden a personas reales.

**Contraseña:** la misma para todas, tomada de la variable `SEED_DEFAULT_PASSWORD` del `.env` al ejecutar el seed (mínimo 8 caracteres). No se publica en el repositorio; pídela al responsable de la demo o define la tuya en tu entorno local.

| Correo | Rol | Alcance |
|---|---|---|
| `director@edutrack.pe` | Director | Todo el colegio: panorama, registro y edición de estudiantes, cálculo de riesgo, alertas |
| `analista@edutrack.pe` | Analista | Todo el colegio: registro y edición de estudiantes, cálculo de riesgo y **configuración de umbrales** (no carga notas) |
| `docente1@edutrack.pe` | Docente (Ciencias) | Carga y corrección de notas de **sus** cursos |
| `docente2@edutrack.pe` | Docente (Letras) | Carga y corrección de notas de **sus** cursos |
| `tutor1@edutrack.pe` | Tutor de 3° A | Su aula: estudiantes, alertas, cálculo de riesgo, corrección de nombres |
| `tutor2@edutrack.pe` | Tutor de 3° B | Su aula |
| `tutor3@edutrack.pe` | Tutor de 4° A | Su aula |
| `padre@edutrack.pe` | Apoderado | Solo al primer estudiante de 3° A |
| `padre2@edutrack.pe` | Apoderada | Solo al primer estudiante de 4° A |

Datos del seed: 1 colegio, 3 aulas (3° A, 3° B, 4° A), 90 estudiantes sintéticos con notas, asistencia y conducta.

> En la demo pública de Vercel (datos simulados, sin backend) no se usan estas cuentas: la pantalla de acceso ofrece botones «Entrar como …» por rol, que inician una sesión simulada.
