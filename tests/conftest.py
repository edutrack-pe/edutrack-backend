import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401
from app.db import get_session
from app.main import app
from app.seed_data import poblar
from app.services import ml_client

PASSWORD = "clave-de-prueba-123"


def ml_falso(solicitudes: list[dict]) -> list[dict]:
    """Simula edutrack-ml: riesgo según el promedio."""
    salida = []
    for s in solicitudes:
        p = max(0.0, min(1.0, (16 - s["features"]["promedio"]) / 8))
        riesgo = "rojo" if p >= s["umbral_rojo"] else "amarillo" if p >= s["umbral_amarillo"] else "verde"
        salida.append({"student_id": s["student_id"], "riesgo": riesgo, "probabilidad": round(p, 3),
                       "factores": ["promedio", "inasistencias", "tareas_entregadas_pct"] if riesgo != "verde" else [],
                       "modelo_version": "rf-prueba"})
    return salida


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        poblar(s, PASSWORD, alumnos_por_aula=6)

    def _session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    monkeypatch.setattr(ml_client, "predecir_lote", ml_falso)
    monkeypatch.setattr("app.main.init_db", lambda: None)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def login(client):
    def _login(email: str) -> dict:
        r = client.post("/api/auth/login", data={"username": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login
