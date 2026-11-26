"""Genera archivos SINTÉTICOS de ejemplo para probar la carga masiva (HU03).

Uso:  python scripts/generar_ejemplos.py [carpeta_destino]

Los códigos A0001… coinciden con el seed de demostración (scripts/seed.py) y el usuario
docente1@edutrack.pe dicta Matemática en todas las aulas. No contienen datos personales reales.
"""

import csv
import io
import sys
import zipfile
from pathlib import Path

from openpyxl import Workbook

CABECERA_NOTAS = ["codigo_estudiante", "curso", "bimestre", "nota"]
VALIDAS = [[f"A{n:04d}", "Matemática", 2, 10 + n % 9] for n in range(1, 13)]


def _csv(ruta: Path, filas: list[list]) -> None:
    with ruta.open("w", newline="", encoding="utf-8-sig") as f:  # BOM: Excel abre bien las tildes
        csv.writer(f).writerows(filas)


def _xlsx(ruta: Path, filas: list[list]) -> None:
    libro = Workbook()
    for fila in filas:
        libro.active.append(fila)
    libro.save(ruta)


def _docx_minimo(ruta: Path) -> None:
    """Documento Word válido y mínimo: el sistema debe rechazarlo por formato."""
    tipos = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/'
             'content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
             'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName='
             '"/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.'
             'document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/'
            '2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    doc = ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Notas en Word (formato no permitido)</w:t></w:r>'
           '</w:p></w:body></w:document>')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("[Content_Types].xml", tipos)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
    ruta.write_bytes(buffer.getvalue())


def generar(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    error_fila_12 = [CABECERA_NOTAS] + [fila[:] for fila in VALIDAS]
    error_fila_12[11][3] = "quince"  # índice 11 = fila 12 del archivo (la 1 es la cabecera)
    archivos = {
        "notas_validas.csv": [CABECERA_NOTAS] + VALIDAS,
        "notas_validas.xlsx": [CABECERA_NOTAS] + [[c, cu, b, n] for c, cu, b, n in VALIDAS[:6]],
        "notas_error_fila_12.csv": error_fila_12,
        "notas_duplicadas.csv": [CABECERA_NOTAS, VALIDAS[0], VALIDAS[0]],
        "asistencias_validas.csv": [["codigo_estudiante", "fecha", "presente"],
                                    ["A0001", "2026-03-16", 1], ["A0002", "2026-03-16", 0],
                                    ["A0003", "2026-03-16", "sí"]],
    }
    rutas = []
    for nombre, filas in archivos.items():
        ruta = destino / nombre
        (_xlsx if nombre.endswith(".xlsx") else _csv)(ruta, filas)
        rutas.append(ruta)
    rutas.append(destino / "notas_no_permitido.docx")
    _docx_minimo(rutas[-1])
    return rutas


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "docs" / "ejemplos-carga"
    for r in generar(carpeta):
        print(r)
