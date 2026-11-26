# Reporte de seguridad · MVP TB4

Alcance: los tres repositorios en la rama `feature/mvp-tb4`. Revisión de dependencias (pip-audit, npm audit), secretos versionados y controles de acceso. No se hicieron pruebas de penetración ni se revisó infraestructura AWS (no hay evidencia de despliegue).

## 1. Dependencias

### Python (pip-audit)
| Repositorio | Paquete | Antes | Vulnerabilidades | Después |
|---|---|---|---|---|
| backend | cryptography | 44.0.0 | 12 | 50.0.2 |
| backend | pyjwt | 2.10.1 | 22 | 2.15.1 |
| backend | python-multipart | 0.0.20 | 12 | 0.0.34 |
| backend | starlette (vía fastapi) | 0.41.3 | 14 | 1.10.0 (fastapi 0.165.0) |
| ml | starlette (vía fastapi) | antigua | sí | fastapi 0.165.0 |

**Resultado final: 0 vulnerabilidades conocidas en backend y ML.** Evidencia: `evidencias/seguridad/pip-audit-{backend,ml}-{antes,despues}.json`. Las 67 + 15 pruebas pasan con las versiones nuevas.

### Frontend (npm audit)
| Momento | Críticas | Altas | Moderadas | Total |
|---|---|---|---|---|
| Antes | 3 | 7 | 5 | 15 |
| Después | 2 | 0 | 7 | 9 |

Se fijaron versiones exactas (axios 1.21.1, react-router-dom 6.30.6, vite 6.4.6, vitest 3.2.7, @playwright/test 1.65.1).
**Riesgo residual (O‑03):** las 2 críticas son de `vitest`/`tinypool`, **solo de desarrollo** (no llegan al *bundle* publicado). Las 7 moderadas requieren saltos mayores (vitest 5, react-router 7) que cambian APIs; se dejan para una iteración posterior. Evidencia: `evidencias/seguridad/npm-audit-frontend.json` (estado **antes** de las correcciones).

## 2. Secretos
- Ningún repositorio versiona `.env`, bases de datos, modelos `.joblib` ni llaves (verificado con `git ls-files`).
- La contraseña de los usuarios demo sale de `SEED_DEFAULT_PASSWORD`; las pruebas E2E y Locust la leen de variables de entorno.
- `.env.example` contiene solo marcadores.

## 3. Controles verificados por pruebas
| Control | Prueba |
|---|---|
| Contraseñas con bcrypt; credenciales incorrectas no revelan si el usuario existe | `test_credenciales_incorrectas_no_generan_token` |
| JWT HS256 de 8 h; 401 si falta, venció o la firma no coincide | `test_token_*`, `test_sin_token_401` |
| RBAC por endpoint (403) | `tests/test_auth_rbac.py`, `test_rol_sin_permiso_403` |
| Aislamiento por aula (tutor) y por hijo (apoderado) | `test_portal_familiar_aislado`, `test_alertas_…_por_tutor` |
| Solo el docente del curso carga y corrige notas | `test_solo_el_docente_importa`, `test_corregir_nota_y_conducta` |
| Carga transaccional, validación de extensión y tamaño (≤ 5 MB) | `test_formato_no_permitido`, `test_archivo_demasiado_grande` |
| ORM con parámetros (sin SQL concatenado) | revisión de código |
| Familia no ve probabilidades numéricas | FE `seguimiento.test.tsx` |

## 3b. Base de datos (MySQL 8.4 local)
- **En tránsito:** el backend se conectaba sin TLS (D‑13). Corregido con `DATABASE_SSL_CA`; las conexiones del *pool* quedan en TLSv1.3 (`TLS_AES_256_GCM_SHA384`).
- **En reposo:** desactivado en el contenedor local; en RDS depende de crear la instancia con cifrado KMS (sin evidencia, O‑08).
- Contraseñas con bcrypt (`$2b$`, 60 caracteres) verificadas directamente en la tabla `user`.
- Detalle en `DATABASE_REPORT.md`.

## 4. Riesgos abiertos
| ID | Riesgo | Impacto | Recomendación |
|---|---|---|---|
| O‑02 | Sin límite de intentos en `/auth/login` | Fuerza bruta (mitigada parcialmente por bcrypt) | `slowapi` o límite en el proxy/API Gateway |
| O‑04 | Token en `localStorage` | Robo del token ante un XSS | Cookie `HttpOnly` + `SameSite` |
| — | Si falta `JWT_SECRET`, se usa un valor por defecto de desarrollo | Tokens falsificables en un despliegue mal configurado | Fallar al arrancar si `ENV=production` y no hay secreto |
| — | Swagger `/docs` público | Exposición del contrato | Desactivar o proteger en producción |
| O‑03 | Dependencias de desarrollo del frontend | Solo entorno de desarrollo | Migrar a vitest 5 / react-router 7 |
| O‑05 | Infraestructura AWS sin verificar | Desconocido | Revisar SG, cifrado RDS y TLS cuando exista despliegue |
