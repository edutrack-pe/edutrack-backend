"""Carga masiva de notas y asistencias desde CSV/Excel (RF-03, HU03) con plantilla fija.

La carga es transaccional: primero se validan TODAS las filas y, si alguna tiene un error, no se inserta
ningún registro. Así se evitan cargas parciales e inconsistentes (escenario 02 de HU03).
"""

import io
from datetime import date

import pandas as pd
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Asistencia, Curso, Estudiante, Nota

PLANTILLAS = {
    "notas": ["codigo_estudiante", "curso", "bimestre", "nota"],
    "asistencias": ["codigo_estudiante", "fecha", "presente"],
}
EXTENSIONES = (".csv", ".xlsx")
FORMATO_NO_PERMITIDO = "Formato no permitido, adjunte un archivo CSV o XLSX"
MAX_FILAS = 5000
SI = {"1", "si", "sí", "true", "p", "presente"}
NO = {"0", "no", "false", "f", "falta", "ausente"}


def leer_archivo(nombre: str, contenido: bytes) -> pd.DataFrame:
    nombre = nombre.lower()
    if not nombre.endswith(EXTENSIONES):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, FORMATO_NO_PERMITIDO)
    if not contenido:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo está vacío")
    try:
        if nombre.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(contenido), dtype=str, engine="openpyxl")
        else:
            df = pd.read_csv(io.BytesIO(contenido), dtype=str, encoding="utf-8-sig", sep=None, engine="python")
    except Exception as e:  # archivo corrupto o con otro formato real
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"No se pudo leer el archivo: {e}") from e
    if len(df) > MAX_FILAS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"El archivo supera el máximo de {MAX_FILAS} filas")
    return df


def _vacio(valor) -> bool:
    return valor is None or (isinstance(valor, float) and pd.isna(valor)) or str(valor).strip() == ""


def importar(session: Session, tipo: str, df: pd.DataFrame, docente_id: int | None = None) -> dict:
    """Valida todas las filas y solo inserta si no hay errores.

    Con `docente_id`, las notas solo se aceptan para los cursos que dicta ese docente.
    """
    columnas = PLANTILLAS[tipo]
    df.columns = [str(c).strip().lower() for c in df.columns]
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Faltan columnas obligatorias: {', '.join(faltantes)}. Use la plantilla: {', '.join(columnas)}",
        )
    df = df.dropna(how="all")
    if df.empty:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo no tiene filas de datos")

    estudiantes = {e.codigo: e for e in session.exec(select(Estudiante))}
    aulas_docente = set(session.exec(select(Curso.aula_id).where(Curso.docente_id == docente_id))) \
        if docente_id is not None else set()
    errores: list[str] = []
    registros: list[Nota | Asistencia] = []
    vistos: set[tuple] = set()

    for i, fila in df.iterrows():
        n = int(i) + 2  # fila en Excel (1 = cabecera)

        def error(texto: str) -> None:
            errores.append(f"Error en la fila {n}: {texto}")

        if any(_vacio(fila[c]) for c in columnas):
            error("hay campos obligatorios vacíos")
            continue
        codigo = str(fila["codigo_estudiante"]).strip().upper()
        est = estudiantes.get(codigo)
        if not est:
            error(f"el estudiante {codigo} no existe")
            continue

        if tipo == "notas":
            nombre_curso = str(fila["curso"]).strip()
            curso = session.exec(
                select(Curso).where(Curso.aula_id == est.aula_id, Curso.nombre == nombre_curso)
            ).first()
            if not curso:
                error(f"el curso {nombre_curso} no existe en el aula del estudiante")
                continue
            if docente_id is not None and curso.docente_id != docente_id:
                error(f"no dictas el curso {curso.nombre} en el aula del estudiante")
                continue
            try:
                valor = float(str(fila["nota"]).replace(",", "."))
            except ValueError:
                error("formato de nota inválido")
                continue
            if not 0 <= valor <= 20:
                error("la nota debe estar entre 0 y 20")
                continue
            try:
                bimestre = int(float(str(fila["bimestre"])))
            except ValueError:
                error("formato de bimestre inválido")
                continue
            if not 1 <= bimestre <= 4:
                error("el bimestre debe estar entre 1 y 4")
                continue
            clave = (est.id, curso.id, bimestre)
            if clave in vistos:
                error(f"registro duplicado en el archivo ({codigo}, {curso.nombre}, bimestre {bimestre})")
                continue
            existente = session.exec(select(Nota.id).where(
                Nota.estudiante_id == est.id, Nota.curso_id == curso.id, Nota.bimestre == bimestre)).first()
            if existente:
                error(f"ya existe la nota de {curso.nombre} del bimestre {bimestre} para {codigo}")
                continue
            vistos.add(clave)
            registros.append(Nota(estudiante_id=est.id, curso_id=curso.id, bimestre=bimestre, valor=round(valor, 2)))
        else:
            if docente_id is not None and est.aula_id not in aulas_docente:
                error(f"no dictas cursos en el aula de {codigo}")
                continue
            texto = str(fila["presente"]).strip().lower()
            if texto not in SI | NO:
                error("el campo presente debe ser 1/0 o sí/no")
                continue
            try:
                fecha: date = pd.to_datetime(str(fila["fecha"]).strip(), dayfirst=False).date()
            except (ValueError, TypeError):
                error("formato de fecha inválido (use AAAA-MM-DD)")
                continue
            if fecha > date.today():
                error("la fecha de asistencia no puede ser futura")
                continue
            clave = (est.id, fecha)
            if clave in vistos:
                error(f"registro duplicado en el archivo ({codigo}, {fecha})")
                continue
            if session.exec(select(Asistencia.id).where(
                    Asistencia.estudiante_id == est.id, Asistencia.fecha == fecha)).first():
                error(f"ya existe la asistencia del {fecha} para {codigo}")
                continue
            vistos.add(clave)
            registros.append(Asistencia(estudiante_id=est.id, fecha=fecha, presente=texto in SI))

    if errores:
        session.rollback()
        return {"filas": int(len(df)), "insertados": 0, "errores": errores}

    try:
        session.add_all(registros)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"filas": int(len(df)), "insertados": len(registros), "errores": []}
