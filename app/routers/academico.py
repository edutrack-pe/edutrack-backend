"""Registro de notas, asistencias, ingesta masiva y encuestas sociofamiliares."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select

from app.core.security import get_current_user, require_role
from app.db import get_session
from app.models import Asistencia, Curso, EncuestaSociofamiliar, Nota, Rol, User
from app.schemas import AsistenciaIn, AsistenciaOut, EncuestaIn, IngestaOut, NotaIn, NotaOut
from app.services.acceso import obtener_estudiante
from app.services.ingesta import PLANTILLAS, importar, leer_archivo

router = APIRouter(tags=["académico"])

PUEDEN_REGISTRAR = (Rol.docente, Rol.director, Rol.analista)


@router.get("/notas", response_model=list[NotaOut])
def listar_notas(estudiante_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    obtener_estudiante(session, user, estudiante_id)
    return session.exec(select(Nota).where(Nota.estudiante_id == estudiante_id)).all()


@router.post("/notas", response_model=NotaOut, status_code=201, summary="RF-02 · Registrar nota")
def registrar_nota(
    data: NotaIn,
    user: User = Depends(require_role(*PUEDEN_REGISTRAR)),
    session: Session = Depends(get_session),
):
    est = obtener_estudiante(session, user, data.estudiante_id)
    curso = session.get(Curso, data.curso_id)
    if not curso or curso.aula_id != est.aula_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El curso no pertenece al aula del estudiante")
    if user.rol == Rol.docente and curso.docente_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puedes registrar notas de tus cursos")
    nota = Nota(**data.model_dump())
    session.add(nota)
    session.commit()
    session.refresh(nota)
    return NotaOut(**nota.model_dump(), curso=curso.nombre)


@router.get("/asistencias", response_model=list[AsistenciaOut])
def listar_asistencias(estudiante_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    obtener_estudiante(session, user, estudiante_id)
    return session.exec(
        select(Asistencia).where(Asistencia.estudiante_id == estudiante_id).order_by(Asistencia.fecha)
    ).all()


@router.post("/asistencias", response_model=AsistenciaOut, status_code=201)
def registrar_asistencia(
    data: AsistenciaIn,
    user: User = Depends(require_role(*PUEDEN_REGISTRAR, Rol.tutor)),
    session: Session = Depends(get_session),
):
    obtener_estudiante(session, user, data.estudiante_id)
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
    _: User = Depends(require_role(Rol.docente, Rol.analista, Rol.director)),
    session: Session = Depends(get_session),
):
    df = leer_archivo(archivo.filename or "", await archivo.read())
    return importar(session, tipo, df)


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
