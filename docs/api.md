# API REST

Documentación interactiva generada automáticamente (OpenAPI):

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Esquema JSON: http://localhost:8000/openapi.json

Todas las rutas usan el prefijo `/api` y requieren `Authorization: Bearer <token>`, salvo `/api/auth/login` y `/api/ingesta/plantilla`.

| Método | Ruta | Roles | Requisito |
|---|---|---|---|
| POST | `/auth/login` (form: `username`=email, `password`) | público | RF-01 |
| GET | `/auth/me` | todos | RF-01 |
| GET | `/aulas` | todos (filtrado por rol) | — |
| GET | `/estudiantes?aula_id=` | todos (filtrado por rol) | RF-02 |
| POST | `/estudiantes` | director, analista | — |
| GET | `/estudiantes/{id}` (ficha completa + predicción + pautas) | con acceso al estudiante | RF-02, RF-07 |
| GET/POST | `/notas` | POST: docente (sus cursos), director, analista | RF-02 |
| GET/POST | `/asistencias` | POST: docente, tutor, director, analista | RF-02 |
| GET | `/ingesta/plantilla?tipo=notas\|asistencias` | público | RF-03 |
| POST | `/ingesta/csv?tipo=notas\|asistencias` (multipart `archivo`) | docente, analista, director | RF-03 |
| POST | `/encuestas` | padre (su hijo), tutor, analista | — |
| POST | `/predicciones/aula/{id}?bimestre=1` | analista, director, tutor (su aula) | RF-04 |
| GET | `/predicciones/estudiante/{id}` | con acceso al estudiante | RF-04 |
| GET | `/dashboard/resumen` | director, tutor, analista, docente | RF-05 |
| GET | `/alertas?solo_no_leidas=` | tutor, director | RF-06 |
| PATCH | `/alertas/{id}/leer` | tutor, director | RF-06 |
| GET/POST | `/actas` | tutor (POST), director | RF-08 |
| GET | `/reportes/aula/{id}/pdf` | director, tutor | RF-09 |
| GET | `/config/riesgo` | analista, director | RF-10 |
| PUT | `/config/riesgo` | analista | RF-10 |
| GET | `/calendario?aula_id=&proximos=true` | todos (filtrado por rol) | Calendario (aviso 8 días) |
| POST | `/calendario` | docente, tutor, director | Calendario |

## Contrato con `edutrack-ml`

El backend llama a `POST {ML_SERVICE_URL}/predict/batch`. Ver el README de `edutrack-ml` para el formato exacto. **Cualquier cambio en el contrato debe coordinarse entre ambos repos.**
