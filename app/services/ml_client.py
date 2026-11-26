"""Cliente HTTP del microservicio edutrack-ml."""

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings


def predecir_lote(solicitudes: list[dict]) -> list[dict]:
    """POST /predict/batch → [{student_id, riesgo, probabilidad, factores}]"""
    if not solicitudes:
        return []
    url = f"{get_settings().ml_service_url.rstrip('/')}/predict/batch"
    try:
        r = httpx.post(url, json=solicitudes, timeout=30)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"El servicio de ML no respondió correctamente: {e}"
        ) from e
    return r.json()


def info_modelo() -> dict:
    """GET /modelo → versión, variables, umbral y evaluación del modelo publicado."""
    url = f"{get_settings().ml_service_url.rstrip('/')}/modelo"
    try:
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"El servicio de ML no respondió correctamente: {e}"
        ) from e
    return r.json()
