"""Criterios de aceptación de las historias Must Have (HU01, HU02, HU04, HU05, HU06 y HU07)."""

from datetime import datetime, timezone

import jwt
import pytest

from app.core.config import get_settings
from app.services import ml_client

# ---------------------------------------------------------------- HU01


def test_token_dura_8_horas_y_lleva_el_rol(client, monkeypatch):
    from app.core.config import Settings

    assert Settings.model_fields["jwt_expires_minutes"].default == 480  # valor por defecto del TB4: 8 horas
    # El .env local puede sobrescribirlo; aquí se verifica que el token respeta el valor configurado.
    monkeypatch.setattr(get_settings(), "jwt_expires_minutes", 480)
    r = client.post("/api/auth/login", data={"username": "tutor1@edutrack.pe", "password": "clave-de-prueba-123"})
    datos = jwt.decode(r.json()["access_token"], get_settings().jwt_secret, algorithms=["HS256"])
    horas = (datos["exp"] - datetime.now(timezone.utc).timestamp()) / 3600
    assert 7.9 < horas <= 8.0
    assert datos["rol"] == "tutor"


def test_credenciales_incorrectas_no_generan_token(client):
    r = client.post("/api/auth/login", data={"username": "tutor1@edutrack.pe", "password": "otra"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Credenciales incorrectas"}


@pytest.mark.parametrize("ruta", ["/api/estudiantes", "/api/dashboard/resumen", "/api/alertas", "/api/aulas"])
def test_sin_token_401(client, ruta):
    assert client.get(ruta).status_code == 401


def test_token_vencido_o_alterado_401(client):
    s = get_settings()
    vencido = jwt.encode({"sub": "1", "rol": "director", "exp": 1}, s.jwt_secret, algorithm="HS256")
    alterado = jwt.encode({"sub": "1", "rol": "director", "exp": 4_000_000_000}, "otro-secreto", algorithm="HS256")
    for token in (vencido, alterado):
        assert client.get("/api/estudiantes", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_rol_sin_permiso_403(client, login):
    docente = login("docente1@edutrack.pe")
    assert client.put("/api/config/riesgo", headers=docente, json={"umbral_amarillo": 0.4, "umbral_rojo": 0.7}).status_code == 403
    assert client.get("/api/alertas", headers=docente).status_code == 403
    assert client.get("/api/dashboard/resumen", headers=login("padre@edutrack.pe")).status_code == 403

# ---------------------------------------------------------------- HU02


def _aulas(client, h):
    return client.get("/api/aulas", headers=h).json()


def _bajar_notas(client, login, est_id: int, valor: float = 4) -> None:
    """Cada docente corrige las notas de sus propios cursos (escenario de bajo rendimiento)."""
    for correo in ("docente1@edutrack.pe", "docente2@edutrack.pe"):
        h = login(correo)
        propios = {c["id"] for c in client.get("/api/cursos", headers=h).json()}
        for nota in client.get(f"/api/notas?estudiante_id={est_id}", headers=h).json():
            if nota["curso_id"] in propios:
                assert client.put(f"/api/notas/{nota['id']}", headers=h, json={"valor": valor}).status_code == 200


def test_registrar_editar_y_persistir_estudiante(client, login):
    director = login("director@edutrack.pe")
    aulas = _aulas(client, director)
    padre2 = next(a for a in client.get("/api/apoderados", headers=director).json() if a["email"] == "padre2@edutrack.pe")
    nuevo = client.post("/api/estudiantes", headers=director, json={
        "codigo": " b0101 ", "nombres": "  Sintético ", "apellidos": "Prueba   Demo", "aula_id": aulas[0]["id"],
    })
    assert nuevo.status_code == 201, nuevo.text
    est = nuevo.json()
    assert (est["codigo"], est["nombres"], est["apellidos"]) == ("B0101", "Sintético", "Prueba Demo")

    editado = client.put(f"/api/estudiantes/{est['id']}", headers=director, json={
        "nombres": "Sintética", "apellidos": "Prueba Demo", "aula_id": aulas[1]["id"], "apoderado_id": padre2["id"],
    })
    assert editado.status_code == 200, editado.text
    # Persistencia: se vuelve a leer desde la base con otra sesión y otro usuario.
    ficha = client.get(f"/api/estudiantes/{est['id']}", headers=login("analista@edutrack.pe")).json()
    assert ficha["estudiante"]["nombres"] == "Sintética"
    assert ficha["estudiante"]["aula_id"] == aulas[1]["id"]
    assert ficha["estudiante"]["apoderado_id"] == padre2["id"]
    hijos = client.get("/api/estudiantes", headers=login("padre2@edutrack.pe")).json()
    assert est["id"] in [h["id"] for h in hijos]


@pytest.mark.parametrize("cambios, estado", [
    ({"codigo": "A0001"}, 409),            # duplicado
    ({"codigo": "123"}, 422),              # formato de código
    ({"nombres": "   "}, 422),             # obligatorio
    ({"aula_id": 9999}, 404),
    ({"apoderado_id": 1}, 422),            # el usuario 1 es el director, no un apoderado
])
def test_validaciones_de_registro(client, login, cambios, estado):
    director = login("director@edutrack.pe")
    datos = {"codigo": "C0001", "nombres": "Ana", "apellidos": "Demo", "aula_id": _aulas(client, director)[0]["id"]}
    assert client.post("/api/estudiantes", headers=director, json=datos | cambios).status_code == estado


def test_permisos_de_edicion(client, login):
    tutor = login("tutor1@edutrack.pe")
    propio = client.get("/api/estudiantes", headers=tutor).json()[0]
    base = {"nombres": "Corregido", "apellidos": propio["apellidos"], "aula_id": propio["aula_id"],
            "apoderado_id": propio["apoderado_id"]}
    assert client.put(f"/api/estudiantes/{propio['id']}", headers=tutor, json=base).status_code == 200
    otra_aula = next(a for a in _aulas(client, login("director@edutrack.pe")) if a["id"] != propio["aula_id"])
    assert client.put(f"/api/estudiantes/{propio['id']}", headers=tutor,
                      json=base | {"aula_id": otra_aula["id"]}).status_code == 403
    ajeno = next(e for e in client.get("/api/estudiantes", headers=login("director@edutrack.pe")).json()
                 if e["aula_id"] != propio["aula_id"])
    assert client.put(f"/api/estudiantes/{ajeno['id']}", headers=tutor, json=base).status_code == 403
    assert client.put(f"/api/estudiantes/{propio['id']}", headers=login("docente1@edutrack.pe"), json=base).status_code == 403
    assert client.post("/api/estudiantes", headers=tutor, json={}).status_code in (403, 422)


def test_corregir_nota_y_conducta(client, login):
    docente1, docente2 = login("docente1@edutrack.pe"), login("docente2@edutrack.pe")
    est = client.get("/api/estudiantes", headers=docente1).json()[0]
    notas = client.get(f"/api/notas?estudiante_id={est['id']}", headers=docente1).json()
    mate = next(n for n in notas if n["curso"] == "Matemática")
    assert client.put(f"/api/notas/{mate['id']}", headers=docente1, json={"valor": 18}).json()["valor"] == 18
    assert client.put(f"/api/notas/{mate['id']}", headers=docente2, json={"valor": 5}).status_code == 403
    assert client.put(f"/api/notas/{mate['id']}", headers=docente1, json={"valor": 21}).status_code == 422
    assert client.put("/api/notas/99999", headers=docente1, json={"valor": 10}).status_code == 404
    duplicada = client.post("/api/notas", headers=docente1, json={
        "estudiante_id": est["id"], "curso_id": mate["curso_id"], "bimestre": mate["bimestre"], "valor": 12})
    assert duplicada.status_code == 409

    tutor = login("tutor1@edutrack.pe")
    c1 = client.put("/api/conducta", headers=tutor, json={"estudiante_id": est["id"], "bimestre": 2, "valor": 2})
    c2 = client.put("/api/conducta", headers=tutor, json={"estudiante_id": est["id"], "bimestre": 2, "valor": 1,
                                                          "observacion": "Mejoró su participación"})
    assert c1.json()["id"] == c2.json()["id"]  # actualiza, no duplica
    ficha = client.get(f"/api/estudiantes/{est['id']}", headers=tutor).json()
    assert [(c["bimestre"], c["valor"]) for c in ficha["conducta"]] == [(1, ficha["conducta"][0]["valor"]), (2, 1)]
    assert 0 <= ficha["asistencia_pct"] <= 100
    assert client.put("/api/conducta", headers=login("padre@edutrack.pe"),
                      json={"estudiante_id": est["id"], "bimestre": 2, "valor": 1}).status_code == 403


def test_cursos_visibles_por_rol(client, login):
    cursos_docente = client.get("/api/cursos", headers=login("docente1@edutrack.pe")).json()
    assert cursos_docente and {c["nombre"] for c in cursos_docente} == {"Matemática", "Ciencia y Tecnología"}
    assert len(client.get("/api/cursos", headers=login("director@edutrack.pe")).json()) == 12

# ---------------------------------------------------------------- HU04


def test_datos_insuficientes_no_llama_al_ml(client, login, monkeypatch):
    llamadas = []
    monkeypatch.setattr(ml_client, "predecir_lote", lambda s: llamadas.append(s) or [])
    analista = login("analista@edutrack.pe")
    aula = _aulas(client, analista)[0]["id"]
    r = client.post(f"/api/predicciones/aula/{aula}?bimestre=3", headers=analista)
    assert r.status_code == 422
    assert r.json()["detail"] == "Datos insuficientes: registre las calificaciones del bimestre actual"
    assert llamadas == []


def test_prediccion_individual_guarda_version_y_fecha(client, login):
    analista = login("analista@edutrack.pe")
    est = client.get("/api/estudiantes", headers=analista).json()[0]
    pred = client.post(f"/api/predicciones/estudiante/{est['id']}?bimestre=1", headers=analista)
    assert pred.status_code == 200, pred.text
    body = pred.json()
    assert body["estudiante_id"] == est["id"] and body["modelo_version"] == "rf-prueba"
    assert body["fecha"] and 0 <= body["probabilidad"] <= 1
    historial = client.get(f"/api/predicciones/estudiante/{est['id']}", headers=analista).json()
    assert historial[0]["id"] == body["id"]
    assert client.post(f"/api/predicciones/estudiante/{est['id']}", headers=login("docente1@edutrack.pe")).status_code == 403


def test_la_prediccion_cambia_si_cambian_los_datos(client, login):
    """La probabilidad sale de las variables reales del estudiante, no de valores fijos."""
    analista = login("analista@edutrack.pe")
    est = client.get("/api/estudiantes", headers=analista).json()[0]
    antes = client.post(f"/api/predicciones/estudiante/{est['id']}", headers=analista).json()
    _bajar_notas(client, login, est["id"])
    despues = client.post(f"/api/predicciones/estudiante/{est['id']}", headers=analista).json()
    assert despues["probabilidad"] > antes["probabilidad"]

# ---------------------------------------------------------------- HU05


def test_dashboard_consistente_y_filtros(client, login):
    analista, director = login("analista@edutrack.pe"), login("director@edutrack.pe")
    aulas = _aulas(client, director)
    client.post(f"/api/predicciones/aula/{aulas[0]['id']}", headers=analista)

    d = client.get("/api/dashboard/resumen", headers=director).json()
    assert d["total_estudiantes"] == 18 and d["evaluados"] == 6 and d["sin_calcular"] == 12
    assert d["verde"] + d["amarillo"] + d["rojo"] == d["evaluados"]
    assert round(sum(d["porcentajes"].values())) == 100
    rojos = client.get("/api/estudiantes?riesgo=rojo", headers=director).json()
    assert len(rojos) == d["rojo"]
    assert len(client.get("/api/estudiantes?sin_calcular=true", headers=director).json()) == 12

    tercero = client.get("/api/dashboard/resumen?grado=3", headers=director).json()
    assert {a["aula"] for a in tercero["aulas"]} == {"3° A", "3° B"}
    b = client.get("/api/dashboard/resumen?grado=3&seccion=b", headers=director).json()
    assert [a["aula"] for a in b["aulas"]] == ["3° B"] and b["evaluados"] == 0
    assert b["porcentajes"] == {"verde": 0.0, "amarillo": 0.0, "rojo": 0.0}
    assert client.get("/api/dashboard/resumen?grado=5", headers=director).json()["aulas"] == []
    assert len(client.get("/api/estudiantes?grado=4", headers=director).json()) == 6


def test_tutor_solo_ve_su_aula_en_el_dashboard(client, login):
    d = client.get("/api/dashboard/resumen", headers=login("tutor1@edutrack.pe")).json()
    assert [a["aula"] for a in d["aulas"]] == ["3° A"]

# ---------------------------------------------------------------- HU06


def test_alertas_con_detalle_sin_duplicados_y_por_tutor(client, login):
    analista = login("analista@edutrack.pe")
    aula = _aulas(client, analista)[0]["id"]
    for est in client.get(f"/api/estudiantes?aula_id={aula}", headers=analista).json()[:2]:
        _bajar_notas(client, login, est["id"])
    primera = client.post(f"/api/predicciones/aula/{aula}", headers=analista).json()
    rojos = primera["resumen"]["rojo"]
    assert rojos > 0, "el escenario de prueba necesita al menos un estudiante en riesgo alto"
    assert primera["alertas_generadas"] == rojos

    segunda = client.post(f"/api/predicciones/aula/{aula}", headers=analista).json()
    assert segunda["alertas_generadas"] == 0  # se actualizan las pendientes, no se duplican

    tutor1 = login("tutor1@edutrack.pe")
    alertas = client.get("/api/alertas", headers=tutor1).json()
    assert len(alertas) == rojos
    a = alertas[0]
    assert a["riesgo"] == "rojo" and a["estudiante"] and a["aula"] == "3° A" and a["factores"]
    detalle = client.get(f"/api/alertas/{a['id']}", headers=tutor1).json()
    assert detalle["prediccion_id"] == a["prediccion_id"]

    # Escenario 02: otro tutor no recibe ni puede abrir la alerta.
    tutor2 = login("tutor2@edutrack.pe")
    assert client.get("/api/alertas", headers=tutor2).json() == []
    assert client.get(f"/api/alertas/{a['id']}", headers=tutor2).status_code == 404
    assert client.patch(f"/api/alertas/{a['id']}/leer", headers=tutor2).status_code == 404

    # Escenario 03: marcar como leída reduce el contador y persiste.
    assert client.patch(f"/api/alertas/{a['id']}/leer", headers=tutor1).json()["leida"] is True
    pendientes = client.get("/api/alertas?solo_no_leidas=true", headers=tutor1).json()
    assert len(pendientes) == rojos - 1
    assert client.get(f"/api/alertas/{a['id']}", headers=login("tutor1@edutrack.pe")).json()["leida"] is True

# ---------------------------------------------------------------- HU07


def test_portal_familiar_aislado(client, login):
    padre, padre2 = login("padre@edutrack.pe"), login("padre2@edutrack.pe")
    hijos = client.get("/api/estudiantes", headers=padre).json()
    hijos2 = client.get("/api/estudiantes", headers=padre2).json()
    assert len(hijos) == 1 and len(hijos2) == 1 and hijos[0]["id"] != hijos2[0]["id"]

    client.post(f"/api/predicciones/estudiante/{hijos[0]['id']}", headers=login("analista@edutrack.pe"))
    ficha = client.get(f"/api/estudiantes/{hijos[0]['id']}", headers=padre).json()
    assert ficha["notas"] and ficha["asistencia_pct"] is not None and ficha["prediccion"]
    assert ficha["pautas"], "debe incluir recomendaciones para el hogar"

    for ruta in (f"/api/estudiantes/{hijos2[0]['id']}", f"/api/notas?estudiante_id={hijos2[0]['id']}",
                 f"/api/asistencias?estudiante_id={hijos2[0]['id']}",
                 f"/api/predicciones/estudiante/{hijos2[0]['id']}"):
        assert client.get(ruta, headers=padre).status_code == 403, ruta
    assert client.get("/api/aulas", headers=padre).json()[0]["id"] == hijos[0]["aula_id"]


def test_pautas_sin_lenguaje_estigmatizante():
    from app.services.pautas import PAUTAS, generar_pautas

    prohibidas = ("fracaso", "flojo", "culpa", "malo", "incapaz", "problemático")
    for textos in PAUTAS.values():
        for t in textos:
            assert not any(p in t.lower() for p in prohibidas), t
    assert generar_pautas(["inasistencias"], "rojo")[0][1].startswith("Asegure la asistencia")
