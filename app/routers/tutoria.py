"""Actas de tutoría (RF-08) y calendario de evaluaciones con aviso de 8 días."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.security import get_current_user, require_role
from app.db import get_session
from app.models import ActaTutoria, EventoCalendario, Rol, User
from app.schemas import ActaIn, ActaOut, EventoIn, EventoOut
from app.services.acceso import aulas_visibles, obtener_estudiante, verificar_aula

router = APIRouter(tags=["tutoría"])

DIAS_AVISO = 8


@router.get("/actas", response_model=list[ActaOut])
def listar_actas(estudiante_id: int, user: User = Depends(require_role(Rol.tutor, Rol.director)),
                 session: Session = Depends(get_session)):
    obtener_estudiante(session, user, estudiante_id)
    return session.exec(
        select(ActaTutoria).where(ActaTutoria.estudiante_id == estudiante_id).order_by(ActaTutoria.fecha.desc())
    ).all()


@router.post("/actas", response_model=ActaOut, status_code=201, summary="RF-08 · Registrar acta de tutoría")
def crear_acta(data: ActaIn, user: User = Depends(require_role(Rol.tutor)), session: Session = Depends(get_session)):
    obtener_estudiante(session, user, data.estudiante_id)
    acta = ActaTutoria(**data.model_dump(), tutor_id=user.id)
    session.add(acta)
    session.commit()
    session.refresh(acta)
    return acta


@router.get("/calendario", response_model=list[EventoOut], summary="Evaluaciones; `proximos=true` = próximos 8 días")
def calendario(
    aula_id: int | None = None,
    proximos: bool = False,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    q = select(EventoCalendario).order_by(EventoCalendario.fecha)
    visibles = aulas_visibles(session, user)
    if aula_id is not None:
        q = q.where(EventoCalendario.aula_id == aula_id)
    if visibles is not None:
        q = q.where(EventoCalendario.aula_id.in_(visibles or [-1]))
    hoy = date.today()
    if proximos:
        q = q.where(EventoCalendario.fecha >= hoy, EventoCalendario.fecha <= hoy + timedelta(days=DIAS_AVISO))
    return [EventoOut(**e.model_dump(), dias_restantes=(e.fecha - hoy).days) for e in session.exec(q)]


@router.post("/calendario", response_model=EventoOut, status_code=201)
def crear_evento(
    data: EventoIn,
    user: User = Depends(require_role(Rol.docente, Rol.tutor, Rol.director)),
    session: Session = Depends(get_session),
):
    verificar_aula(session, user, data.aula_id)
    evento = EventoCalendario(**data.model_dump())
    session.add(evento)
    session.commit()
    session.refresh(evento)
    return EventoOut(**evento.model_dump(), dias_restantes=(evento.fecha - date.today()).days)
