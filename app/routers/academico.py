"""Registro de notas, asistencias, ingesta masiva y encuestas sociofamiliares."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select

from app.core.security import get_current_user, require_role
from app.db import get_session
from app.models import Asistencia, Conducta, Curso, EncuestaSociofamiliar, Nota, Rol, User
from app.schemas import (
    AsistenciaIn, AsistenciaOut, ConductaIn, ConductaOut, EncuestaIn, IngestaOut, NotaIn, NotaOut, NotaUpdate,
)
from app.services.acceso import obtener_estudiante
from app.services.ingesta import MAX_BYTES, PLANTILLAS, importar, leer_archivo

router = APIRouter(tags=["académico"])

# Solo el docente registra notas (de sus cursos); director, analista, tutor y apoderado las consultan.
PUEDEN_REGISTRAR_NOTAS = (Rol.docente,)
PUEDEN_REGISTRAR_ASISTENCIA = (Rol.docente, Rol.director, Rol.analista, Rol.tutor)


@router.get("/notas", response_model=list[NotaOut])
def listar_notas(estudiante_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    obtener_estudiante(session, user, estudiante_id)
    filas = session.exec(
        select(Nota, Curso.nombre).join(Curso, Curso.id == Nota.curso_id)
        .where(Nota.estudiante_id == estudiante_id).order_by(Nota.bimestre, Curso.nombre)
    ).all()
    return [NotaOut(**n.model_dump(), curso=c) for n, c in filas]


@router.post("/notas", response_model=NotaOut, status_code=201, summary="RF-02 · Registrar nota")
def registrar_nota(
    data: NotaIn,
    user: User = Depends(require_role(*PUEDEN_REGISTRAR_NOTAS)),
    session: Session = Depends(get_session),
):
    est = obtener_estudiante(session, user, data.estudiante_id)
    curso = session.get(Curso, data.curso_id)
    if not curso or curso.aula_id != est.aula_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El curso no pertenece al aula del estudiante")
    if curso.docente_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puedes registrar notas de tus cursos")
    if session.exec(select(Nota.id).where(Nota.estudiante_id == est.id, Nota.curso_id == curso.id,
                                          Nota.bimestre == data.bimestre)).first():
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Ya existe la nota de este curso y bimestre; edítela en lugar de registrarla otra vez")
    nota = Nota(**data.model_dump())
    session.add(nota)
    session.commit()
    session.refresh(nota)
    return NotaOut(**nota.model_dump(), curso=curso.nombre)


@router.put("/notas/{nota_id}", response_model=NotaOut, summary="HU02 · Corregir una nota")
def editar_nota(
    nota_id: int,
    data: NotaUpdate,
    user: User = Depends(require_role(*PUEDEN_REGISTRAR_NOTAS)),
    session: Session = Depends(get_session),
):
    nota = session.get(Nota, nota_id)
    if not nota:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nota no encontrada")
    curso = session.get(Curso, nota.curso_id)
    if curso.docente_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puedes corregir notas de tus cursos")
    nota.valor = data.valor
    session.add(nota)
    session.commit()
    session.refresh(nota)
    return NotaOut(**nota.model_dump(), curso=curso.nombre)


@router.put("/conducta", response_model=ConductaOut, summary="HU02 · Registrar o actualizar la conducta del bimestre")
def registrar_conducta(
    data: ConductaIn,
    user: User = Depends(require_role(Rol.tutor, Rol.docente)),
    session: Session = Depends(get_session),
):
    obtener_estudiante(session, user, data.estudiante_id)  # tutor: sus aulas · docente: aulas donde dicta
    registro = session.exec(select(Conducta).where(
        Conducta.estudiante_id == data.estudiante_id, Conducta.bimestre == data.bimestre)).first()
    if registro:
        registro.valor, registro.observacion = data.valor, data.observacion
    else:
        registro = Conducta(**data.model_dump())
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return registro


@router.get("/asistencias", response_model=list[AsistenciaOut])
def listar_asistencias(estudiante_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    obtener_estudiante(session, user, estudiante_id)
    return session.exec(
        select(Asistencia).where(Asistencia.estudiante_id == estudiante_id).order_by(Asistencia.fecha)
    ).all()


@router.post("/asistencias", response_model=AsistenciaOut, status_code=201)
def registrar_asistencia(
    data: AsistenciaIn,
    user: User = Depends(require_role(*PUEDEN_REGISTRAR_ASISTENCIA)),
    session: Session = Depends(get_session),
):
    obtener_estudiante(session, user, data.estudiante_id)
    if session.exec(select(Asistencia.id).where(Asistencia.estudiante_id == data.estudiante_id,
                                                Asistencia.fecha == data.fecha)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe la asistencia de ese día para el estudiante")
    a = Asistencia(**data.model_dump())
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


@router.get("/ingesta/plantilla", response_class=PlainTextResponse, summary="Descargar plantilla CSV")
def plantilla(tipo: str = Query("notas", pattern="^(notas|asistencias)$")):
    ejemplo = {
        "notas": "A0001,Matemática,1,14",
        "asistencias": "A0001,2026-03-10,1",
    }[tipo]
    return f"{','.join(PLANTILLAS[tipo])}\n{ejemplo}\n"


@router.post("/ingesta/csv", response_model=IngestaOut, summary="RF-03 · Carga masiva CSV/Excel")
async def ingesta(
    tipo: str = Query("notas", pattern="^(notas|asistencias)$"),
    archivo: UploadFile = File(...),
    user: User = Depends(require_role(*PUEDEN_REGISTRAR_NOTAS)),
    session: Session = Depends(get_session),
):
    contenido = await archivo.read(MAX_BYTES + 1)  # no se lee más allá del límite
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "El archivo supera el tamaño máximo de 5 MB")
    df = leer_archivo(archivo.filename or "", contenido)
    return importar(session, tipo, df, docente_id=user.id)


@router.post("/encuestas", status_code=201, summary="Encuesta sociofamiliar (apoderado)")
def registrar_encuesta(
    data: EncuestaIn,
    user: User = Depends(require_role(Rol.padre, Rol.analista, Rol.tutor)),
    session: Session = Depends(get_session),
):
    obtener_estudiante(session, user, data.estudiante_id)
    encuesta = EncuestaSociofamiliar(**data.model_dump())
    session.add(encuesta)
    session.commit()
    return {"id": encuesta.id, "mensaje": "Encuesta registrada. ¡Gracias por su participación!"}
