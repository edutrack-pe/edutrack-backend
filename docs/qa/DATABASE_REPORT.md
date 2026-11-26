# Evidencia de base de datos · MySQL 8

**Fecha:** 26/11/2026 · **Motor:** MySQL Community **8.4.13** (imagen oficial `mysql:8.4`, la misma de `infra/docker-compose.yml`) en un contenedor Docker local, puerto 3318, base `edutrack`, `utf8mb4` / `utf8mb4_0900_ai_ci`.
**Datos:** únicamente sintéticos (seed + datos creados por el E2E integral).

> Esto es una verificación **local** sobre MySQL real. No es AWS RDS: no se afirma nada sobre la instancia RDS, su red ni su cifrado en reposo (ver §5).

## 1. Esquema y migraciones
| Verificación | Resultado |
|---|---|
| `alembic upgrade head` sobre una base vacía | ✅ versión `0001_inicial` |
| `alembic check` (modelos vs. base) | ✅ «No new upgrade operations detected» |
| Tablas creadas | 18 (17 del dominio + `alembic_version`), todas InnoDB |
| Restricciones únicas | `uq_nota_estudiante_curso_bimestre`, `uq_asistencia_estudiante_fecha`, `uq_conducta_estudiante_bimestre`, `ix_estudiante_codigo`, `ix_user_email` |
| Claves foráneas | 24 (todas las relaciones del modelo) |

La deduplicación de alertas (HU06) **no** es una restricción de la base: el servicio `_registrar_alerta` actualiza la alerta sin leer del estudiante en lugar de crear otra. Está verificada por `test_alertas_con_detalle_sin_duplicados_y_por_tutor`.

## 2. Suite del backend sobre MySQL
`conftest.py` admite `TEST_DATABASE_URL`: la **misma** suite (sin cambiar ninguna prueba) crea y borra el esquema en MySQL en cada prueba.

| Corrida | Resultado |
|---|---|
| SQLite en memoria (por defecto, CI) | 70 pasan · 1 omitida (requiere MySQL real) |
| MySQL 8.4 (`edutrack_test`) con `TEST_DATABASE_SSL_CA` | ✅ **71 pasan** en 4 min 53 s (incluye la prueba de TLS real) · `evidencias/base-datos/pytest-mysql.txt` |

## 3. Persistencia del flujo completo (E2E integral sobre MySQL con TLS)
Base nueva → `alembic upgrade head` → seed (9 usuarios, 3 aulas, 90 estudiantes) → backend con TLS hacia MySQL → `playwright.integral.config.ts`: **8/8 escenarios pasan** (`evidencias/base-datos/e2e-integral-mysql-tls.json`).

Estado de la base al terminar (`evidencias/base-datos/consultas-mysql.txt`):
| Dato | Valor |
|---|---|
| Estudiantes | 91 (90 del seed + 1 registrado por el E2E) |
| Notas | 364 · Asistencias 1 800 |
| Predicciones | 31 (aula 3° A), todas con `modelo_version = rf-20261126-9ad6a250`, probabilidad 0,0152–0,9607 |
| Niveles | 22 verde · 4 amarillo · 5 rojo |
| Alertas | 5 (1 marcada como leída por el E2E) |
| Auditoría | crear_estudiante 1 · editar_estudiante 1 · ver_ficha 6 |

Los resultados coinciden con la corrida sobre SQLite (mismo estudiante nuevo: amarillo, 0,6561).

## 4. Contraseñas
Las 9 contraseñas se guardan como hash **bcrypt** (`$2b$`, 60 caracteres). La evidencia muestra solo prefijo y longitud, nunca el hash ni la clave.

## 5. Cifrado
### En tránsito (backend → MySQL)
| Momento | Conexiones del backend | Evidencia |
|---|---|---|
| Antes | `TCP/IP` **sin TLS** (`Ssl_version` vacío): el backend no pedía cifrado aunque el servidor lo soporta | hallazgo D‑13 |
| Después | `SSL/TLS`, **TLSv1.3**, `TLS_AES_256_GCM_SHA384` en las 5 conexiones del *pool* | `evidencias/base-datos/tls-conexiones-backend.txt` |

Corrección: `DATABASE_SSL_CA` (ruta de la CA; en RDS, el *bundle* de AWS) activa TLS con verificación del certificado; `DATABASE_SSL_VERIFY_HOSTNAME` (por defecto `true`). En la prueba local se desactivó la verificación del nombre porque el certificado autogenerado de MySQL no lleva el nombre del host; **en RDS debe quedar en `true`**. Pruebas: `tests/test_db.py` (3 unitarias + 1 contra el MySQL real que comprueba `Ssl_cipher`).

El servidor de prueba tiene `require_secure_transport = OFF`. En producción debe activarse (en RDS: parámetro `require_secure_transport = 1`) para rechazar conexiones sin TLS.

### En reposo
En el contenedor local `default_table_encryption`, `innodb_redo_log_encrypt`, `innodb_undo_log_encrypt` y `binlog_encryption` están en **OFF**: **no hay cifrado en reposo en esta verificación**. En AWS se resuelve al crear la instancia RDS con *storage encryption* (KMS); **no hay evidencia** de que exista esa instancia (O‑05).

## 6. Cómo reproducir
```bash
docker run -d --name edutrack-mysql -p 127.0.0.1:3318:3306 -e MYSQL_ROOT_PASSWORD=<clave> \
  -e MYSQL_DATABASE=edutrack -e MYSQL_USER=edutrack -e MYSQL_PASSWORD=<clave> mysql:8.4
docker cp edutrack-mysql:/var/lib/mysql/ca.pem ./mysql-ca.pem

export DATABASE_URL="mysql+pymysql://edutrack:<clave>@127.0.0.1:3318/edutrack"
export DATABASE_SSL_CA=./mysql-ca.pem DATABASE_SSL_VERIFY_HOSTNAME=false
alembic upgrade head && alembic check && python scripts/seed.py

# suite completa sobre MySQL (base aparte)
TEST_DATABASE_URL="mysql+pymysql://edutrack:<clave>@127.0.0.1:3318/edutrack_test" \
TEST_DATABASE_SSL_CA=./mysql-ca.pem TEST_DATABASE_SSL_VERIFY_HOSTNAME=false pytest
```
