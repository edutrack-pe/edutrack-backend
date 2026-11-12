# Modelo de datos (MySQL)

Definido en [`app/models/__init__.py`](../app/models/__init__.py) con SQLModel.

```mermaid
erDiagram
    USER ||--o{ AULA : "tutorea"
    USER ||--o{ CURSO : "dicta"
    USER ||--o{ ESTUDIANTE : "es apoderado de"
    COLEGIO ||--|{ AULA : tiene
    AULA ||--|{ ESTUDIANTE : agrupa
    AULA ||--|{ CURSO : tiene
    AULA ||--o{ EVENTOCALENDARIO : programa
    ESTUDIANTE ||--o{ NOTA : obtiene
    CURSO ||--o{ NOTA : califica
    ESTUDIANTE ||--o{ ASISTENCIA : registra
    ESTUDIANTE ||--o{ CONDUCTA : registra
    ESTUDIANTE ||--o{ TAREA : entrega
    ESTUDIANTE ||--o{ ENCUESTASOCIOFAMILIAR : responde
    ESTUDIANTE ||--o{ PREDICCION : recibe
    PREDICCION ||--|{ PAUTA : genera
    ESTUDIANTE ||--o{ ALERTA : dispara
    USER ||--o{ ALERTA : recibe
    ESTUDIANTE ||--o{ ACTATUTORIA : tiene
    USER ||--o{ AUDITLOG : genera

    USER { int id PK; string email UK; string nombre; string hashed_password; enum rol; bool activo }
    COLEGIO { int id PK; string nombre }
    AULA { int id PK; string nombre; int grado; int colegio_id FK; int tutor_id FK }
    ESTUDIANTE { int id PK; string codigo UK; string nombres; string apellidos; int aula_id FK; int apoderado_id FK }
    CURSO { int id PK; string nombre; int aula_id FK; int docente_id FK }
    NOTA { int id PK; int estudiante_id FK; int curso_id FK; int bimestre; float valor }
    ASISTENCIA { int id PK; int estudiante_id FK; date fecha; bool presente }
    CONDUCTA { int id PK; int estudiante_id FK; int bimestre; int valor; string observacion }
    TAREA { int id PK; int estudiante_id FK; int curso_id FK; string titulo; date fecha_entrega; bool entregada }
    ENCUESTASOCIOFAMILIAR { int id PK; int estudiante_id FK; float horas_estudio; int nivel_edu_padres; bool acceso_tecnologia; int tiempo_disponible_padres; int comunicacion_familiar; datetime fecha }
    PREDICCION { int id PK; int estudiante_id FK; int bimestre; enum riesgo; float probabilidad; json factores; datetime fecha }
    PAUTA { int id PK; int prediccion_id FK; int estudiante_id FK; string factor; string texto }
    ALERTA { int id PK; int estudiante_id FK; int tutor_id FK; string mensaje; bool leida; datetime fecha }
    ACTATUTORIA { int id PK; int estudiante_id FK; int tutor_id FK; date fecha; string acuerdos; string compromisos }
    EVENTOCALENDARIO { int id PK; int aula_id FK; int curso_id FK; string titulo; date fecha }
    CONFIGRIESGO { int id PK; float umbral_amarillo; float umbral_rojo }
    AUDITLOG { int id PK; int user_id FK; string accion; string recurso; datetime fecha }
```

## Variables que se envían al modelo

| Variable | Origen |
|---|---|
| `promedio`, `cursos_desaprobados` | `nota` del bimestre (desaprobado = nota < 11) |
| `inasistencias` | `asistencia` con `presente = false` |
| `conducta` | `conducta` del bimestre (1 buena · 2 regular · 3 mala) |
| `tareas_entregadas_pct` | `tarea.entregada` |
| `horas_estudio`, `nivel_edu_padres`, `acceso_tecnologia`, `tiempo_disponible_padres`, `comunicacion_familiar` | última `encuestasociofamiliar` (si no hay, valores neutros) |

## Migraciones

En el MVP las tablas se crean al iniciar la API (`init_db`). Cuando el esquema se estabilice:

```bash
alembic revision --autogenerate -m "esquema inicial"
alembic upgrade head
```
