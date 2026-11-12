"""Reporte PDF consolidado por aula (RF-09) con ReportLab."""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COLORES = {
    "verde": colors.HexColor("#2e7d32"),
    "amarillo": colors.HexColor("#f9a825"),
    "rojo": colors.HexColor("#c62828"),
}


def reporte_aula_pdf(colegio: str, aula: str, filas: list[dict]) -> bytes:
    """filas: [{codigo, nombre, promedio, inasistencias, riesgo, probabilidad}]"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Reporte {aula}")
    estilos = getSampleStyleSheet()

    resumen = {r: sum(1 for f in filas if f["riesgo"] == r) for r in COLORES}
    datos = [["Código", "Estudiante", "Promedio", "Faltas", "Riesgo", "Prob."]]
    for f in filas:
        datos.append([
            f["codigo"], f["nombre"], f"{f['promedio']:.1f}" if f["promedio"] is not None else "-",
            f["inasistencias"], (f["riesgo"] or "sin calcular").upper(),
            f"{f['probabilidad']:.0%}" if f["probabilidad"] is not None else "-",
        ])

    tabla = Table(datos, repeatRows=1, colWidths=[60, 170, 60, 45, 90, 50])
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263238")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]
    for i, f in enumerate(filas, start=1):
        if f["riesgo"] in COLORES:
            estilo += [("TEXTCOLOR", (4, i), (4, i), COLORES[f["riesgo"]]), ("FONTNAME", (4, i), (4, i), "Helvetica-Bold")]
    tabla.setStyle(TableStyle(estilo))

    doc.build([
        Paragraph(f"EduTrack · {colegio}", estilos["Title"]),
        Paragraph(f"Reporte consolidado de riesgo académico · Aula {aula} · {date.today():%d/%m/%Y}", estilos["Normal"]),
        Spacer(1, 10),
        Paragraph(
            f"Riesgo alto: <b>{resumen['rojo']}</b> · moderado: <b>{resumen['amarillo']}</b> · bajo: <b>{resumen['verde']}</b>",
            estilos["Normal"],
        ),
        Spacer(1, 10),
        tabla,
        Spacer(1, 14),
        Paragraph("Documento confidencial. Contiene datos personales de menores de edad (Ley N° 29733).", estilos["Italic"]),
    ])
    return buffer.getvalue()
