from tests.conftest import PASSWORD


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_login_ok_y_me(client, login):
    h = login("director@edutrack.pe")
    me = client.get("/api/auth/me", headers=h).json()
    assert me["rol"] == "director"


def test_login_incorrecto(client):
    r = client.post("/api/auth/login", data={"username": "director@edutrack.pe", "password": "mala"})
    assert r.status_code == 401


def test_sin_token_y_token_invalido(client):
    assert client.get("/api/estudiantes").status_code == 401
    assert client.get("/api/estudiantes", headers={"Authorization": "Bearer xxx"}).status_code == 401


def test_director_ve_todo_tutor_solo_su_aula(client, login):
    todos = client.get("/api/estudiantes", headers=login("director@edutrack.pe")).json()
    tutor = client.get("/api/estudiantes", headers=login("tutor1@edutrack.pe")).json()
    assert len(todos) == 18
    assert len(tutor) == 6
    assert len({e["aula_id"] for e in tutor}) == 1


def test_padre_solo_ve_a_su_hijo(client, login):
    h = login("padre@edutrack.pe")
    hijos = client.get("/api/estudiantes", headers=h).json()
    assert len(hijos) == 1
    otro = client.get("/api/estudiantes", headers=login("director@edutrack.pe")).json()[-1]
    if otro["id"] != hijos[0]["id"]:
        assert client.get(f"/api/estudiantes/{otro['id']}", headers=h).status_code == 403


def test_rol_sin_permiso(client, login):
    r = client.put("/api/config/riesgo", json={"umbral_amarillo": 0.3, "umbral_rojo": 0.6},
                   headers=login("tutor1@edutrack.pe"))
    assert r.status_code == 403


def test_password_no_se_guarda_en_texto_plano(client, login):
    from app.core.security import hash_password, verify_password

    h = hash_password(PASSWORD)
    assert h != PASSWORD and verify_password(PASSWORD, h)
