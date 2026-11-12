def test_registrar_nota_docente_y_restricciones(client, login):
    director = login("director@edutrack.pe")
    est = client.get("/api/estudiantes", headers=director).json()[0]
    ficha = client.get(f"/api/estudiantes/{est['id']}", headers=director).json()
    curso_id = ficha["notas"][0]["curso_id"]  # Ciencia y Tecnología (1.º alfabético) → docente1

    docente1 = login("docente1@edutrack.pe")
    ok = client.post("/api/notas", headers=docente1,
                     json={"estudiante_id": est["id"], "curso_id": curso_id, "bimestre": 2, "valor": 15})
    assert ok.status_code == 201, ok.text

    docente2 = login("docente2@edutrack.pe")
    no = client.post("/api/notas", headers=docente2,
                     json={"estudiante_id": est["id"], "curso_id": curso_id, "bimestre": 2, "valor": 15})
    assert no.status_code == 403

    fuera = client.post("/api/notas", headers=docente1,
                        json={"estudiante_id": est["id"], "curso_id": curso_id, "bimestre": 2, "valor": 25})
    assert fuera.status_code == 422

    notas = client.get(f"/api/notas?estudiante_id={est['id']}", headers=director).json()
    assert len(notas) == 5


def test_asistencia(client, login):
    tutor = login("tutor1@edutrack.pe")
    est = client.get("/api/estudiantes", headers=tutor).json()[0]
    r = client.post("/api/asistencias", headers=tutor,
                    json={"estudiante_id": est["id"], "fecha": "2026-11-10", "presente": False})
    assert r.status_code == 201
    lista = client.get(f"/api/asistencias?estudiante_id={est['id']}", headers=tutor).json()
    assert any(a["fecha"] == "2026-11-10" and not a["presente"] for a in lista)


def test_ingesta_csv(client, login):
    analista = login("analista@edutrack.pe")
    plantilla = client.get("/api/ingesta/plantilla?tipo=notas").text
    assert plantilla.startswith("codigo_estudiante,curso,bimestre,nota")

    csv = "codigo_estudiante,curso,bimestre,nota\nA0001,Matemática,2,13\nA9999,Matemática,2,10\nA0001,Arte,2,12\nA0001,Inglés,9,12\n"
    r = client.post("/api/ingesta/csv?tipo=notas", headers=analista,
                    files={"archivo": ("notas.csv", csv.encode(), "text/csv")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["insertados"] == 1
    assert len(body["errores"]) == 3

    asis = "codigo_estudiante,fecha,presente\nA0001,2026-11-11,0\nA0002,2026-11-11,si\n"
    r = client.post("/api/ingesta/csv?tipo=asistencias", headers=analista,
                    files={"archivo": ("asis.csv", asis.encode(), "text/csv")})
    assert r.json()["insertados"] == 2

    mala = client.post("/api/ingesta/csv?tipo=notas", headers=analista,
                       files={"archivo": ("x.csv", b"col1,col2\n1,2\n", "text/csv")})
    assert mala.status_code == 400


def test_encuesta_padre(client, login):
    padre = login("padre@edutrack.pe")
    hijo = client.get("/api/estudiantes", headers=padre).json()[0]
    r = client.post("/api/encuestas", headers=padre, json={
        "estudiante_id": hijo["id"], "horas_estudio": 5, "nivel_edu_padres": 2, "acceso_tecnologia": True,
        "tiempo_disponible_padres": 2, "comunicacion_familiar": 3,
    })
    assert r.status_code == 201


def test_crear_estudiante(client, login):
    director = login("director@edutrack.pe")
    aula_id = client.get("/api/aulas", headers=director).json()[0]["id"]
    data = {"codigo": "N0001", "nombres": "Nuevo", "apellidos": "Alumno", "aula_id": aula_id}
    assert client.post("/api/estudiantes", headers=director, json=data).status_code == 201
    assert client.post("/api/estudiantes", headers=director, json=data).status_code == 409


def test_pautas_por_reglas():
    from app.services.pautas import generar_pautas

    assert generar_pautas(["promedio"], "verde")[0][0] == "general"
    assert len(generar_pautas(["promedio", "inasistencias"], "rojo")) == 4
    assert len(generar_pautas(["promedio", "desconocido"], "amarillo")) == 2
