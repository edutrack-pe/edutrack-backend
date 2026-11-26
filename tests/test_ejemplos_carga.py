"""Los archivos de ejemplo publicados en docs/ejemplos-carga producen el resultado documentado."""

from pathlib import Path

import pytest

from scripts.generar_ejemplos import generar


@pytest.fixture()
def ejemplos(tmp_path) -> dict[str, Path]:
    return {r.name: r for r in generar(tmp_path)}


def _subir(client, h, ruta: Path, tipo="notas"):
    return client.post(f"/api/ingesta/csv?tipo={tipo}", headers=h, files={"archivo": (ruta.name, ruta.read_bytes())})


def test_ejemplos_de_carga(client, login, ejemplos):
    h = login("docente1@edutrack.pe")
    assert _subir(client, h, ejemplos["notas_error_fila_12.csv"]).json() == {
        "filas": 12, "insertados": 0, "errores": ["Error en la fila 12: formato de nota inválido"]}
    assert "duplicado en el archivo" in _subir(client, h, ejemplos["notas_duplicadas.csv"]).json()["errores"][0]
    noperm = _subir(client, h, ejemplos["notas_no_permitido.docx"])
    assert noperm.status_code == 400
    assert _subir(client, h, ejemplos["notas_validas.xlsx"]).json()["insertados"] == 6
    # El CSV repite seis registros del XLSX: la carga completa se rechaza por duplicados.
    csv = _subir(client, h, ejemplos["notas_validas.csv"]).json()
    assert csv["insertados"] == 0 and len(csv["errores"]) == 6
    assert _subir(client, h, ejemplos["asistencias_validas.csv"], tipo="asistencias").json()["insertados"] == 3
