"""Carga masiva de notas y asistencias desde CSV/Excel (RF-03) con plantilla fija."""

import io

import pandas as pd
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Asistencia, Curso, Estudiante, Nota

PLANTILLAS = {
    "notas": ["codigo_estudiante", "curso", "bimestre", "nota"],
    "asistencias": ["codigo_estudiante", "fecha", "presente"],
}


def leer_archivo(nombre: str, contenido: bytes) -> pd.DataFrame:
    try:
        if nombre.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(contenido))
        return pd.read_csv(io.BytesIO(contenido))
    except Exception as e:  # formato corrupto
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"No se pudo leer el archivo: {e}") from e


def importar(session: Session, tipo: str, df: pd.DataFrame, docente_id: int | None = None) -> dict:
    """Importa el archivo. Con `docente_id`, las notas solo se aceptan para los cursos que dicta ese docente."""
    columnas = PLANTILLAS[tipo]
    df.columns = [str(c).strip().lower() for c in df.columns]
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Faltan columnas: {', '.join(faltantes)}. Esperadas: {columnas}"
        )

    estudiantes = {e.codigo: e for e in session.exec(select(Estudiante))}
    errores: list[str] = []
    insertados = 0

    for i, fila in df.iterrows():
        n = i + 2  # fila en Excel (1 = cabecera)
        est = estudiantes.get(str(fila["codigo_estudiante"]).strip())
        if not est:
            errores.append(f"Fila {n}: estudiante '{fila['codigo_estudiante']}' no existe")
            continue
        try:
            if tipo == "notas":
                curso = session.exec(
                    select(Curso).where(Curso.aula_id == est.aula_id, Curso.nombre == str(fila["curso"]).strip())
                ).first()
                if not curso:
                    errores.append(f"Fila {n}: curso '{fila['curso']}' no existe en el aula del estudiante")
                    continue
                if docente_id is not None and curso.docente_id != docente_id:
                    errores.append(f"Fila {n}: no dictas el curso '{curso.nombre}' en el aula del estudiante")
                    continue
                valor, bimestre = float(fila["nota"]), int(fila["bimestre"])
                if not (0 <= valor <= 20 and 1 <= bimestre <= 4):
                    errores.append(f"Fila {n}: nota (0-20) o bimestre (1-4) fuera de rango")
                    continue
                session.add(Nota(estudiante_id=est.id, curso_id=curso.id, bimestre=bimestre, valor=valor))
            else:
                presente = str(fila["presente"]).strip().lower() in {"1", "si", "sí", "true", "p"}
                fecha = pd.to_datetime(fila["fecha"]).date()
                session.add(Asistencia(estudiante_id=est.id, fecha=fecha, presente=presente))
            insertados += 1
        except (ValueError, TypeError) as e:
            errores.append(f"Fila {n}: valor inválido ({e})")

    session.commit()
    return {"insertados": insertados, "errores": errores}
