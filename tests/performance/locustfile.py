"""Prueba de carga (RNF-01: p95 ≤ 2 s) de los endpoints críticos de EduTrack con Locust.

Requiere el backend y edutrack-ml levantados con el seed de demostración (datos sintéticos).

    pip install locust==2.32.4
    EDUTRACK_PASSWORD=<clave del seed> locust -f tests/performance/locustfile.py --headless \
        -u 30 -r 5 -t 3m --host http://localhost:8000 --csv reports/locust --html reports/locust.html

No se ejecuta en CI ni contra producción: mide un entorno local o de staging controlado.
"""

import os
import random

from locust import HttpUser, between, task

CLAVE = os.environ.get("EDUTRACK_PASSWORD", "")


class _Base(HttpUser):
    abstract = True
    wait_time = between(1, 3)
    correo = ""

    def on_start(self) -> None:
        r = self.client.post("/api/auth/login", data={"username": self.correo, "password": CLAVE}, name="POST /auth/login")
        r.raise_for_status()
        self.client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        self.estudiantes = [e["id"] for e in self.client.get("/api/estudiantes", name="GET /estudiantes").json()]


class Director(_Base):
    """Consulta el panorama y las fichas (lectura intensiva)."""
    weight = 3
    correo = "director@edutrack.pe"

    @task(4)
    def dashboard(self) -> None:
        self.client.get("/api/dashboard/resumen", name="GET /dashboard/resumen")

    @task(2)
    def dashboard_filtrado(self) -> None:
        self.client.get(f"/api/dashboard/resumen?grado={random.choice([3, 4])}", name="GET /dashboard/resumen?grado")

    @task(3)
    def lista(self) -> None:
        self.client.get("/api/estudiantes", name="GET /estudiantes")

    @task(3)
    def ficha(self) -> None:
        self.client.get(f"/api/estudiantes/{random.choice(self.estudiantes)}", name="GET /estudiantes/{id}")


class Tutor(_Base):
    """Revisa alertas y fichas de su aula."""
    weight = 2
    correo = "tutor1@edutrack.pe"

    @task(3)
    def alertas(self) -> None:
        self.client.get("/api/alertas?solo_no_leidas=true", name="GET /alertas")

    @task(2)
    def ficha(self) -> None:
        self.client.get(f"/api/estudiantes/{random.choice(self.estudiantes)}", name="GET /estudiantes/{id}")


class Analista(_Base):
    """Ejecuta predicciones (llama al microservicio ML con el Random Forest real)."""
    weight = 1
    correo = "analista@edutrack.pe"

    @task(1)
    def predecir_aula(self) -> None:
        self.client.post(f"/api/predicciones/aula/{random.choice([1, 2, 3])}?bimestre=1", name="POST /predicciones/aula/{id}")

    @task(3)
    def predecir_estudiante(self) -> None:
        self.client.post(f"/api/predicciones/estudiante/{random.choice(self.estudiantes)}?bimestre=1",
                         name="POST /predicciones/estudiante/{id}")


class Padre(_Base):
    """Consulta el portal familiar."""
    weight = 1
    correo = "padre@edutrack.pe"

    @task
    def portal(self) -> None:
        self.client.get(f"/api/estudiantes/{self.estudiantes[0]}", name="GET /estudiantes/{id} (padre)")
