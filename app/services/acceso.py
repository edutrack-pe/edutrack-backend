"""Reglas de visibilidad por rol (RBAC a nivel de datos).

- director / analista: todo el colegio
- tutor: estudiantes de las aulas que tutorea
- docente: estudiantes de las aulas donde dicta algún curso
- padre: solo sus hijos (apoderado_id)
"""

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Aula, AuditLog, Curso, Estudiante, Rol, User


def aulas_visibles(session: Session, user: User) -> list[int] | None:
    """Ids de aulas visibles. None = todas."""
    if user.rol in (Rol.director, Rol.analista):
        return None
    if user.rol == Rol.tutor:
        return list(session.exec(select(Aula.id).where(Aula.tutor_id == user.id)))
    if user.rol == Rol.docente:
        return list(set(session.exec(select(Curso.aula_id).where(Curso.docente_id == user.id))))
    hijos = session.exec(select(Estudiante.aula_id).where(Estudiante.apoderado_id == user.id))
    return list(set(hijos))


def estudiantes_query(session: Session, user: User):
    q = select(Estudiante)
    if user.rol == Rol.padre:
        return q.where(Estudiante.apoderado_id == user.id)
    aulas = aulas_visibles(session, user)
    if aulas is not None:
        q = q.where(Estudiante.aula_id.in_(aulas or [-1]))
    return q


def puede_ver_estudiante(session: Session, user: User, est: Estudiante) -> bool:
    if user.rol == Rol.padre:
        return est.apoderado_id == user.id
    aulas = aulas_visibles(session, user)
    return aulas is None or est.aula_id in aulas


def obtener_estudiante(session: Session, user: User, estudiante_id: int) -> Estudiante:
    est = session.get(Estudiante, estudiante_id)
    if not est:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estudiante no encontrado")
    if not puede_ver_estudiante(session, user, est):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a este estudiante")
    return est


def verificar_aula(session: Session, user: User, aula_id: int) -> Aula:
    aula = session.get(Aula, aula_id)
    if not aula:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aula no encontrada")
    aulas = aulas_visibles(session, user)
    if aulas is not None and aula_id not in aulas:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a esta aula")
    return aula


def auditar(session: Session, user: User, accion: str, recurso: str) -> None:
    session.add(AuditLog(user_id=user.id, accion=accion, recurso=recurso))
    session.commit()
