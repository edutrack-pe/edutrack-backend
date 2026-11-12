from datetime import date, timedelta


def _aula_tutor1(client, h):
    return client.get("/api/aulas", headers=h).json()[0]["id"]


def test_prediccion_dashboard_alertas_y_ficha(client, login):
    analista = login("analista@edutrack.pe")
    aula_id = client.get("/api/aulas", headers=analista).json()[0]["id"]

    r = client.post(f"/api/predicciones/aula/{aula_id}?bimestre=1", headers=analista)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["procesados"] == 6
    assert sum(res["resumen"].values()) == 6

    dash = client.get("/api/dashboard/resumen", headers=login("director@edutrack.pe")).json()
    aula = next(a for a in dash["aulas"] if a["aula_id"] == aula_id)
    assert aula["sin_calcular"] == 0
    assert dash["total_estudiantes"] == 18

    est = client.get(f"/api/estudiantes?aula_id={aula_id}", headers=analista).json()[0]
    ficha = client.get(f"/api/estudiantes/{est['id']}", headers=analista).json()
    assert ficha["prediccion"]["riesgo"] in {"verde", "amarillo", "rojo"}
    assert ficha["pautas"], "debe generar pautas"
    assert len(ficha["notas"]) == 4

    historial = client.get(f"/api/predicciones/estudiante/{est['id']}", headers=analista).json()
    assert len(historial) == 1

    tutor = login("tutor1@edutrack.pe")
    alertas = client.get("/api/alertas", headers=tutor).json()
    rojos = res["resumen"]["rojo"]
    assert len(alertas) == rojos
    if alertas:
        leida = client.patch(f"/api/alertas/{alertas[0]['id']}/leer", headers=tutor).json()
        assert leida["leida"] is True
        assert len(client.get("/api/alertas?solo_no_leidas=true", headers=tutor).json()) == rojos - 1


def test_umbrales_configurables(client, login):
    analista = login("analista@edutrack.pe")
    assert client.get("/api/config/riesgo", headers=analista).json()["umbral_rojo"] == 0.7
    r = client.put("/api/config/riesgo", json={"umbral_amarillo": 0.01, "umbral_rojo": 0.02}, headers=analista)
    assert r.status_code == 200
    bad = client.put("/api/config/riesgo", json={"umbral_amarillo": 0.9, "umbral_rojo": 0.2}, headers=analista)
    assert bad.status_code == 422


def test_tutor_no_predice_aula_ajena(client, login):
    director = login("director@edutrack.pe")
    aulas = client.get("/api/aulas", headers=director).json()
    r = client.post(f"/api/predicciones/aula/{aulas[-1]['id']}", headers=login("tutor1@edutrack.pe"))
    assert r.status_code == 403


def test_reporte_pdf(client, login):
    director = login("director@edutrack.pe")
    aula_id = _aula_tutor1(client, director)
    r = client.get(f"/api/reportes/aula/{aula_id}/pdf", headers=director)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_actas_y_calendario(client, login):
    tutor = login("tutor1@edutrack.pe")
    aula_id = _aula_tutor1(client, tutor)
    est = client.get("/api/estudiantes", headers=tutor).json()[0]

    acta = client.post("/api/actas", headers=tutor, json={
        "estudiante_id": est["id"], "fecha": str(date.today()),
        "acuerdos": "Reforzar matemática 30 min diarios", "compromisos": "El apoderado revisará la agenda",
    })
    assert acta.status_code == 201
    assert len(client.get(f"/api/actas?estudiante_id={est['id']}", headers=tutor).json()) == 1

    ev = client.post("/api/calendario", headers=tutor, json={
        "aula_id": aula_id, "titulo": "Práctica calificada", "fecha": str(date.today() + timedelta(days=2)),
    })
    assert ev.status_code == 201 and ev.json()["dias_restantes"] == 2
    proximos = client.get("/api/calendario?proximos=true", headers=tutor).json()
    assert all(0 <= e["dias_restantes"] <= 8 for e in proximos)
    assert any(e["titulo"] == "Práctica calificada" for e in proximos)
