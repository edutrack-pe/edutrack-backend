"""Aulas, estudiantes (HU02: registro, consulta y edición) y ficha académica."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select

from app.core.security import get_current_user, require_role
from app.db import get_session
from app.models import Asistencia, Aula, Conducta, Curso, Estudiante, Nota, Pauta, Riesgo, Rol, Tarea, User
from app.schemas import (
    ApoderadoOut, AulaOut, ConductaOut, CursoOut, EstudianteIn, EstudianteOut, EstudianteUpdate, FichaEstudiante,
    NotaOut, PautaOut, PrediccionOut,
)
from app.services.acceso import aulas_visibles, auditar, estudiantes_query, obtener_estudiante, verificar_aula
from app.services.prediccion import ultima_prediccion, ultimas_predicciones

router = APIRouter(tags=["estudiantes"])


@router.get("/aulas", response_model=list[AulaOut])
def listar_aulas(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    q = select(Aula).order_by(Aula.grado, Aula.seccion)
    visibles = aulas_visibles(session, user)
    if visibles is not None:
        q = q.where(Aula.id.in_(visibles or [-1]))
    return session.exec(q).all()


@router.get("/cursos", response_model=list[CursoOut], summary="Cursos visibles (el docente solo ve los suyos)")
def listar_cursos(
    aula_id: int | None = None, user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    q = select(Curso).order_by(Curso.aula_id, Curso.nombre)
    if user.rol == Rol.docente:
        q = q.where(Curso.docente_id == user.id)
    else:
        visibles = aulas_visibles(session, user)
        if visibles is not None:
            q = q.where(Curso.aula_id.in_(visibles or [-1]))
    if aula_id is not None:
        q = q.where(Curso.aula_id == aula_id)
    return session.exec(q).all()


@router.get("/apoderados", response_model=list[ApoderadoOut], summary="Apoderados que se pueden asociar")
def listar_apoderados(
    _: User = Depends(require_role(Rol.director, Rol.analista)), session: Session = Depends(get_session),
):
    return session.exec(select(User).where(User.rol == Rol.padre, User.activo == True).order_by(User.nombre)).all()  # noqa: E712


@router.get("/estudiantes", response_model=list[EstudianteOut], summary="Lista con último nivel de riesgo")
def listar_estudiantes(
    aula_id: int | None = None,
    grado: int | None = Query(None, ge=1, le=5),
    seccion: str | None = Query(None, max_length=5),
    riesgo: Riesgo | None = None,
    sin_calcular: bool = False,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    q = estudiantes_query(session, user)
    if aula_id is not None:
        q = q.where(Estudiante.aula_id == aula_id)
    if grado is not None or seccion:
        q = q.join(Aula, Aula.id == Estudiante.aula_id)
        if grado is not None:
            q = q.where(Aula.grado == grado)
        if seccion:
            q = q.where(Aula.seccion == seccion.strip().upper())
    estudiantes = list(session.exec(q.order_by(Estudiante.apellidos, Estudiante.nombres)))
    preds = ultimas_predicciones(session, [e.id for e in estudiantes])
    salida = []
    for est in estudiantes:
        pred = preds.get(est.id)
        if riesgo is not None and (not pred or pred.riesgo != riesgo):
            continue
        if sin_calcular and pred:
            continue
        salida.append(EstudianteOut(**est.model_dump(), riesgo=pred.riesgo if pred else None,
                                    probabilidad=pred.probabilidad if pred else None))
    return salida


def _validar_relaciones(session: Session, data: EstudianteIn | EstudianteUpdate) -> None:
    if not session.get(Aula, data.aula_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aula no encontrada")
    if data.apoderado_id is not None:
        apoderado = session.get(User, data.apoderado_id)
        if not apoderado or apoderado.rol != Rol.padre:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El apoderado indicado no existe")


@router.post("/estudiantes", response_model=EstudianteOut, status_code=201, summary="HU02 · Registrar estudiante")
def crear_estudiante(
    data: EstudianteIn,
    user: User = Depends(require_role(Rol.director, Rol.analista)),
    session: Session = Depends(get_session),
):
    if session.exec(select(Estudiante).where(Estudiante.codigo == data.codigo)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un estudiante con ese código")
    _validar_relaciones(session, data)
    est = Estudiante(**data.model_dump())
    session.add(est)
    session.commit()
    session.refresh(est)
    salida = EstudianteOut(**est.model_dump())
    auditar(session, user, "crear_estudiante", f"estudiante:{est.id}")
    return salida


@router.put("/estudiantes/{estudiante_id}", response_model=EstudianteOut, summary="HU02 · Editar datos del estudiante")
def editar_estudiante(
    estudiante_id: int,
    data: EstudianteUpdate,
    user: User = Depends(require_role(Rol.director, Rol.analista, Rol.tutor)),
    session: Session = Depends(get_session),
):
    est = obtener_estudiante(session, user, estudiante_id)
    if user.rol == Rol.tutor and (data.aula_id != est.aula_id or data.apoderado_id != est.apoderado_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El tutor solo puede corregir nombres y apellidos")
    _validar_relaciones(session, data)
    if user.rol != Rol.tutor:
        verificar_aula(session, user, data.aula_id)
    for campo, valor in data.model_dump().items():
        setattr(est, campo, valor)
    session.add(est)
    session.commit()
    session.refresh(est)
    pred = ultima_prediccion(session, est.id)
    salida = EstudianteOut(**est.model_dump(), riesgo=pred.riesgo if pred else None,
                           probabilidad=pred.probabilidad if pred else None)
    auditar(session, user, "editar_estudiante", f"estudiante:{est.id}")
    return salida


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
    conducta = session.exec(select(Conducta).where(Conducta.estudiante_id == est.id).order_by(Conducta.bimestre)).all()
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
        asistencia_pct=round(100 * (total - faltas) / total, 1) if total else None,
        conducta=[ConductaOut(**c.model_dump()) for c in conducta],
        tareas_entregadas_pct=round(sum(tareas) / len(tareas), 3) if tareas else None,
        prediccion=PrediccionOut(**pred.model_dump()) if pred else None,
        pautas=[PautaOut(factor=p.factor, texto=p.texto) for p in pautas],
    )
