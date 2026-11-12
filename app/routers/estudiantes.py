from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, func, select

from app.core.security import get_current_user, require_role
from app.db import get_session
from app.models import Asistencia, Aula, Curso, Estudiante, Nota, Pauta, Rol, Tarea, User
from app.schemas import (
    AulaOut, EstudianteIn, EstudianteOut, FichaEstudiante, NotaOut, PautaOut, PrediccionOut,
)
from app.services.acceso import aulas_visibles, auditar, estudiantes_query, obtener_estudiante
from app.services.prediccion import ultima_prediccion

router = APIRouter(tags=["estudiantes"])


@router.get("/aulas", response_model=list[AulaOut])
def listar_aulas(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    q = select(Aula).order_by(Aula.grado, Aula.nombre)
    visibles = aulas_visibles(session, user)
    if visibles is not None:
        q = q.where(Aula.id.in_(visibles or [-1]))
    return session.exec(q).all()


@router.get("/estudiantes", response_model=list[EstudianteOut], summary="Lista con último nivel de riesgo")
def listar_estudiantes(
    aula_id: int | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    q = estudiantes_query(session, user)
    if aula_id is not None:
        q = q.where(Estudiante.aula_id == aula_id)
    salida = []
    for est in session.exec(q.order_by(Estudiante.apellidos)):
        pred = ultima_prediccion(session, est.id)
        salida.append(EstudianteOut(
            **est.model_dump(), riesgo=pred.riesgo if pred else None,
            probabilidad=pred.probabilidad if pred else None,
        ))
    return salida


@router.post("/estudiantes", response_model=EstudianteOut, status_code=201)
def crear_estudiante(
    data: EstudianteIn,
    _: User = Depends(require_role(Rol.director, Rol.analista)),
    session: Session = Depends(get_session),
):
    if session.exec(select(Estudiante).where(Estudiante.codigo == data.codigo)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un estudiante con ese código")
    if not session.get(Aula, data.aula_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aula no encontrada")
    est = Estudiante(**data.model_dump())
    session.add(est)
    session.commit()
    session.refresh(est)
    return EstudianteOut(**est.model_dump())


@router.get("/estudiantes/{estudiante_id}", response_model=FichaEstudiante, summary="RF-02 · Ficha del estudiante")
def ficha(estudiante_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    est = obtener_estudiante(session, user, estudiante_id)
    auditar(session, user, "ver_ficha", f"estudiante:{est.id}")

    notas = session.exec(
        select(Nota, Curso.nombre).join(Curso, Curso.id == Nota.curso_id)
        .where(Nota.estudiante_id == est.id).order_by(Nota.bimestre, Curso.nombre)
    ).all()
    total = session.exec(select(func.count()).select_from(Asistencia).where(Asistencia.estudiante_id == est.id)).one()
    faltas = session.exec(
        select(func.count()).select_from(Asistencia)
        .where(Asistencia.estudiante_id == est.id, Asistencia.presente == False)  # noqa: E712
    ).one()
    tareas = list(session.exec(select(Tarea.entregada).where(Tarea.estudiante_id == est.id)))
    pred = ultima_prediccion(session, est.id)
    pautas = session.exec(select(Pauta).where(Pauta.prediccion_id == pred.id)).all() if pred else []

    return FichaEstudiante(
        estudiante=EstudianteOut(**est.model_dump(), riesgo=pred.riesgo if pred else None,
                                 probabilidad=pred.probabilidad if pred else None),
        aula=session.get(Aula, est.aula_id).nombre,
        notas=[NotaOut(**n.model_dump(), curso=c) for n, c in notas],
        asistencias_total=total,
        inasistencias=faltas,
        tareas_entregadas_pct=round(sum(tareas) / len(tareas), 3) if tareas else None,
        prediccion=PrediccionOut(**pred.model_dump()) if pred else None,
        pautas=[PautaOut(factor=p.factor, texto=p.texto) for p in pautas],
    )
