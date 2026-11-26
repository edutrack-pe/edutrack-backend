"""HU03 · Carga masiva transaccional de notas y asistencias (CSV y XLSX)."""

import io
from datetime import date, timedelta

import pytest
from openpyxl import Workbook

CABECERA_NOTAS = "codigo_estudiante,curso,bimestre,nota\n"


def subir(client, headers, contenido: bytes, nombre="notas.csv", tipo="notas"):
    return client.post(f"/api/ingesta/csv?tipo={tipo}", headers=headers, files={"archivo": (nombre, contenido)})


def xlsx(filas: list[list]) -> bytes:
    libro = Workbook()
    hoja = libro.active
    for fila in filas:
        hoja.append(fila)
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def notas_de(client, headers, est_id: int, bimestre: int) -> list[dict]:
    return [n for n in client.get(f"/api/notas?estudiante_id={est_id}", headers=headers).json() if n["bimestre"] == bimestre]


@pytest.fixture()
def docente1(login):
    return login("docente1@edutrack.pe")  # dicta Matemática y Ciencia y Tecnología en todas las aulas


def test_plantillas_publicas(client):
    assert client.get("/api/ingesta/plantilla?tipo=notas").text.startswith(CABECERA_NOTAS)
    assert client.get("/api/ingesta/plantilla?tipo=asistencias").text.startswith("codigo_estudiante,fecha,presente")


def test_csv_valido_se_importa_y_se_puede_consultar(client, docente1):
    csv = CABECERA_NOTAS + "A0001,Matemática,2,13\nA0002,Matemática,2,15.5\na0003,Ciencia y Tecnología,2,09\n"
    r = subir(client, docente1, csv.encode())
    assert r.status_code == 200, r.text
    assert r.json() == {"filas": 3, "insertados": 3, "errores": []}
    est = client.get("/api/estudiantes", headers=docente1).json()
    a1 = next(e for e in est if e["codigo"] == "A0001")
    assert [n["valor"] for n in notas_de(client, docente1, a1["id"], 2)] == [13]


def test_xlsx_valido_se_importa(client, docente1):
    contenido = xlsx([["codigo_estudiante", "curso", "bimestre", "nota"],
                      ["A0001", "Matemática", 3, 17], ["A0002", "Ciencia y Tecnología", 3, 12]])
    r = subir(client, docente1, contenido, nombre="notas_2026.xlsx")
    assert r.status_code == 200, r.text
    assert r.json()["insertados"] == 2


def test_un_error_detiene_toda_la_carga(client, docente1):
    """Escenario 02 de HU03: nota no numérica en la fila 12 → no se inserta nada."""
    filas = [f"A{n:04d},Matemática,2,{10 + n % 8}" for n in range(1, 11)]
    filas.insert(10, "A0011,Matemática,2,quince")
    csv = CABECERA_NOTAS + "\n".join(filas) + "\n"
    r = subir(client, docente1, csv.encode())
    assert r.status_code == 200
    body = r.json()
    assert body["insertados"] == 0
    assert body["errores"] == ["Error en la fila 12: formato de nota inválido"]
    est = client.get("/api/estudiantes", headers=docente1).json()
    a1 = next(e for e in est if e["codigo"] == "A0001")
    assert notas_de(client, docente1, a1["id"], 2) == []


@pytest.mark.parametrize("fila, mensaje", [
    ("A9999,Matemática,2,10", "el estudiante A9999 no existe"),
    ("A0001,Arte,2,12", "el curso Arte no existe en el aula del estudiante"),
    ("A0001,Matemática,2,25", "la nota debe estar entre 0 y 20"),
    ("A0001,Matemática,9,12", "el bimestre debe estar entre 1 y 4"),
    ("A0001,Matemática,,12", "hay campos obligatorios vacíos"),
    ("A0001,Comunicación,2,14", "no dictas el curso Comunicación en el aula del estudiante"),
    ("A0001,Matemática,1,14", "ya existe la nota de Matemática del bimestre 1 para A0001"),
])
def test_validaciones_por_fila(client, docente1, fila, mensaje):
    r = subir(client, docente1, (CABECERA_NOTAS + fila + "\n").encode())
    assert r.json()["errores"] == [f"Error en la fila 2: {mensaje}"]
    assert r.json()["insertados"] == 0


def test_duplicado_dentro_del_archivo(client, docente1):
    csv = CABECERA_NOTAS + "A0001,Matemática,2,13\nA0001,Matemática,2,14\n"
    errores = subir(client, docente1, csv.encode()).json()["errores"]
    assert errores == ["Error en la fila 3: registro duplicado en el archivo (A0001, Matemática, bimestre 2)"]


def test_reimportar_el_mismo_archivo_no_duplica(client, docente1):
    csv = (CABECERA_NOTAS + "A0001,Matemática,2,13\n").encode()
    assert subir(client, docente1, csv).json()["insertados"] == 1
    segunda = subir(client, docente1, csv).json()
    assert segunda["insertados"] == 0
    assert "ya existe la nota" in segunda["errores"][0]


@pytest.mark.parametrize("nombre", ["notas.docx", "notas.pdf", "notas.xls", "notas"])
def test_formato_no_permitido(client, docente1, nombre):
    r = subir(client, docente1, b"contenido", nombre=nombre)
    assert r.status_code == 400
    assert r.json()["detail"] == "Formato no permitido, adjunte un archivo CSV o XLSX"


def test_columnas_faltantes_y_archivo_vacio(client, docente1):
    sin_columnas = subir(client, docente1, b"col1,col2\n1,2\n")
    assert sin_columnas.status_code == 400
    assert "Faltan columnas obligatorias" in sin_columnas.json()["detail"]
    assert subir(client, docente1, b"").status_code == 400
    assert subir(client, docente1, CABECERA_NOTAS.encode()).status_code == 400


def test_archivo_demasiado_grande(client, docente1):
    grande = CABECERA_NOTAS.encode() + b"A0001,Matem\xc3\xa1tica,2,13\n" * 260_000  # > 5 MB
    r = subir(client, docente1, grande)
    assert r.status_code == 413
    assert r.json()["detail"] == "El archivo supera el tamaño máximo de 5 MB"


def test_asistencias(client, docente1):
    ayer = date.today() - timedelta(days=1)
    asis = f"codigo_estudiante,fecha,presente\nA0001,{ayer},0\nA0002,{ayer},sí\n"
    r = subir(client, docente1, asis.encode(), nombre="asistencias.csv", tipo="asistencias")
    assert r.json() == {"filas": 2, "insertados": 2, "errores": []}

    futura = date.today() + timedelta(days=3)
    malas = (f"codigo_estudiante,fecha,presente\nA0001,{ayer},1\nA0003,{futura},1\nA0004,{ayer},tal vez\n"
             "A0005,31/02/2026,1\n")
    errores = subir(client, docente1, malas.encode(), nombre="a.csv", tipo="asistencias").json()["errores"]
    assert errores == [
        f"Error en la fila 2: ya existe la asistencia del {ayer} para A0001",
        "Error en la fila 3: la fecha de asistencia no puede ser futura",
        "Error en la fila 4: el campo presente debe ser 1/0 o sí/no",
        "Error en la fila 5: formato de fecha inválido (use AAAA-MM-DD)",
    ]


def test_solo_el_docente_importa(client, login):
    csv = (CABECERA_NOTAS + "A0001,Matemática,2,13\n").encode()
    for correo in ("director@edutrack.pe", "analista@edutrack.pe", "tutor1@edutrack.pe", "padre@edutrack.pe"):
        assert subir(client, login(correo), csv).status_code == 403, correo
    assert client.post("/api/ingesta/csv?tipo=notas", files={"archivo": ("n.csv", csv)}).status_code == 401
