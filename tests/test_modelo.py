"""GET /api/modelo: ficha del modelo publicado (versión, métricas, matriz de confusión, importancias)."""

import httpx
import pytest

from app.services import ml_client


def _matriz(vn, fp, fn, vp):
    return {"vn": vn, "fp": fp, "fn": fn, "vp": vp}


def _con_umbral(umbral, precision, recall, f1, matriz):
    return {"umbral": umbral, "precision": precision, "recall": recall, "f1": f1, "matriz_confusion": matriz}


# Misma forma que ml-service/reports/metricas.json del modelo rf-20261126-9ad6a250.
INFO_ML = {
    "version": "rf-20261126-9ad6a250",
    "variables_modelo": ["promedio", "inasistencias", "cursos_desaprobados"],
    "umbral_decision": 0.5,
    "metricas": {"f1": 0.7398, "auc_roc": 0.9122},
    "fecha_entrenamiento": "2026-11-26T20:29:37+00:00",
    "evaluacion": {
        "version": "rf-20261126-9ad6a250",
        "datos": {"origen": "sintético", "filas": 2000, "entrenamiento": 1600, "prueba": 400,
                  "proporcion_en_riesgo": 0.283},
        "vif": {"promedio": 1.617, "inasistencias": 1.004, "cursos_desaprobados": 1.617},
        "variables_descartadas_vif": [],
        "mejores_hiperparametros": {"max_depth": 6, "min_samples_leaf": 3, "n_estimators": 400},
        "validacion_cruzada": {"folds": 5, "f1_media": 0.7646, "f1_desviacion": 0.018, "auc_media": 0.9144},
        "prueba": {
            **_con_umbral(0.5, 0.6842, 0.8053, 0.7398, _matriz(245, 42, 22, 91)), "auc_roc": 0.9122,
            "con_umbral_0_5": _con_umbral(0.5, 0.6842, 0.8053, 0.7398, _matriz(245, 42, 22, 91)),
            "con_umbral_sistema_0_4": _con_umbral(0.4, 0.6533, 0.8673, 0.7452, _matriz(235, 52, 15, 98)),
            "con_umbral_alto_0_7": _con_umbral(0.7, 0.7802, 0.6283, 0.6961, _matriz(267, 20, 42, 71)),
        },
        "importancia_variables": {"inasistencias": 0.0524, "promedio": 0.4586, "cursos_desaprobados": 0.3054},
        "metas": {"f1_minimo": 0.75, "auc_minimo_exclusivo": 0.8},
        "cumple_rnf02": False,
    },
}


@pytest.fixture()
def ml_info(monkeypatch):
    def _usar(info):
        monkeypatch.setattr(ml_client, "info_modelo", lambda: info)
    _usar(INFO_ML)
    return _usar


def test_director_ve_la_ficha_real_del_modelo(client, login, ml_info):
    r = client.get("/api/modelo", headers=login("director@edutrack.pe"))
    assert r.status_code == 200
    m = r.json()
    assert m["version"] == "rf-20261126-9ad6a250"
    ev = m["evaluacion"]
    assert ev["prueba"]["f1"] == 0.7398 and ev["prueba"]["auc_roc"] == 0.9122
    assert ev["prueba"]["matriz_confusion"] == {"vn": 245, "fp": 42, "fn": 22, "vp": 91}
    assert ev["cumple_rnf02"] is False
    # importancias ordenadas de mayor a menor y umbrales de sensibilidad en orden creciente
    assert [i["variable"] for i in ev["importancia_variables"]] == ["promedio", "cursos_desaprobados", "inasistencias"]
    assert [s["umbral"] for s in ev["sensibilidad_umbral"]] == [0.4, 0.5, 0.7]
    assert ev["vif_maximo"] == 1.617


def test_analista_tambien_la_ve(client, login, ml_info):
    assert client.get("/api/modelo", headers=login("analista@edutrack.pe")).status_code == 200


@pytest.mark.parametrize("email", ["tutor1@edutrack.pe", "docente1@edutrack.pe", "padre@edutrack.pe"])
def test_otros_roles_no_acceden(client, login, ml_info, email):
    assert client.get("/api/modelo", headers=login(email)).status_code == 403


def test_modelo_sin_evaluacion(client, login, ml_info):
    ml_info({k: v for k, v in INFO_ML.items() if k != "evaluacion"} | {"evaluacion": None})
    r = client.get("/api/modelo", headers=login("director@edutrack.pe"))
    assert r.status_code == 200
    assert r.json()["evaluacion"] is None


def test_ml_caido_responde_502(client, login, monkeypatch):
    def _falla(*_a, **_k):
        raise httpx.ConnectError("sin conexión")

    monkeypatch.setattr(ml_client.httpx, "get", _falla)
    r = client.get("/api/modelo", headers=login("director@edutrack.pe"))
    assert r.status_code == 502
