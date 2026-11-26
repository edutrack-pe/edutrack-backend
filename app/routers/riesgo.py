"""Predicción, dashboard, alertas, reportes y configuración de umbrales."""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlmodel import Session, func, select

from app.core.security import get_current_user, require_role
from app.db import get_session
from app.models import Alerta, Asistencia, Aula, Colegio, Estudiante, Nota, Prediccion, Rol, User
from app.schemas import (
    AlertaOut, ConfigRiesgoIO, DashboardOut, ModeloOut, PrediccionOut, ResultadoPrediccionAula, ResumenAula,
)
from app.services import ml_client
from app.services.acceso import aulas_visibles, auditar, obtener_estudiante, verificar_aula
from app.services.modelo import a_modelo_out
from app.services.prediccion import (
    obtener_config, predecir_aula, predecir_estudiante, ultima_prediccion, ultimas_predicciones,
)
from app.services.reportes import reporte_aula_pdf

router = APIRouter(tags=["riesgo"])


@router.post(
    "/predicciones/aula/{aula_id}", response_model=ResultadoPrediccionAula,
    summary="RF-04 · Calcular el riesgo de todos los estudiantes del aula",
)
def predecir(
    aula_id: int,
    bimestre: int = Query(1, ge=1, le=4),
    user: User = Depends(require_role(Rol.analista, Rol.director, Rol.tutor)),
    session: Session = Depends(get_session),
):
    aula = verificar_aula(session, user, aula_id)
    return predecir_aula(session, aula, bimestre)


@router.post(
    "/predicciones/estudiante/{estudiante_id}", response_model=PrediccionOut,
    summary="RF-04 · Calcular el riesgo de un estudiante",
)
def predecir_uno(
    estudiante_id: int,
    bimestre: int = Query(1, ge=1, le=4),
    user: User = Depends(require_role(Rol.analista, Rol.director, Rol.tutor)),
    session: Session = Depends(get_session),
):
    est = obtener_estudiante(session, user, estudiante_id)
    return predecir_estudiante(session, est, bimestre)


@router.get("/predicciones/estudiante/{estudiante_id}", response_model=list[PrediccionOut])
def historial(estudiante_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    obtener_estudiante(session, user, estudiante_id)
    return session.exec(
        select(Prediccion).where(Prediccion.estudiante_id == estudiante_id).order_by(Prediccion.fecha.desc())
    ).all()


@router.get("/dashboard/resumen", response_model=DashboardOut, summary="RF-05 · Semáforos por aula")
def dashboard(
    grado: int | None = Query(None, ge=1, le=5, description="Filtra por grado (3 = 3.° de secundaria)"),
    seccion: str | None = Query(None, max_length=5, description="Filtra por sección (A, B…)"),
    user: User = Depends(require_role(Rol.director, Rol.tutor, Rol.analista, Rol.docente)),
    session: Session = Depends(get_session),
):
    q = select(Aula).order_by(Aula.grado, Aula.seccion)
    visibles = aulas_visibles(session, user)
    if visibles is not None:
        q = q.where(Aula.id.in_(visibles or [-1]))
    if grado is not None:
        q = q.where(Aula.grado == grado)
    if seccion:
        q = q.where(Aula.seccion == seccion.strip().upper())

    aulas_lista = list(session.exec(q))
    estudiantes = list(session.exec(
        select(Estudiante.id, Estudiante.aula_id).where(Estudiante.aula_id.in_([a.id for a in aulas_lista] or [-1]))
    ))
    preds = ultimas_predicciones(session, [e.id for e in estudiantes])
    conteos = {a.id: {"verde": 0, "amarillo": 0, "rojo": 0, "sin_calcular": 0, "total": 0} for a in aulas_lista}
    for est_id, aula_id in estudiantes:
        pred = preds.get(est_id)
        conteos[aula_id][pred.riesgo.value if pred else "sin_calcular"] += 1
        conteos[aula_id]["total"] += 1
    aulas = [ResumenAula(aula_id=a.id, aula=a.nombre, grado=a.grado, seccion=a.seccion, **conteos[a.id])
             for a in aulas_lista]

    def suma(campo: str) -> int:
        return sum(getattr(a, campo) for a in aulas)

    total, sin_calcular = suma("total"), suma("sin_calcular")
    evaluados = total - sin_calcular
    niveles = {n: suma(n) for n in ("verde", "amarillo", "rojo")}
    porcentajes = {n: round(100 * v / evaluados, 1) if evaluados else 0.0 for n, v in niveles.items()}
    return DashboardOut(total_estudiantes=total, evaluados=evaluados, sin_calcular=sin_calcular,
                        porcentajes=porcentajes, aulas=aulas, **niveles)


@router.get("/alertas", response_model=list[AlertaOut], summary="RF-06 · Alertas del tutor")
def alertas(
    solo_no_leidas: bool = False,
    user: User = Depends(require_role(Rol.tutor, Rol.director)),
    session: Session = Depends(get_session),
):
    q = select(Alerta).order_by(Alerta.fecha.desc(), Alerta.id.desc())
    if user.rol == Rol.tutor:
        q = q.where(Alerta.tutor_id == user.id)
    if solo_no_leidas:
        q = q.where(Alerta.leida == False)  # noqa: E712
    return [_alerta_out(session, a) for a in session.exec(q)]


def _alerta_out(session: Session, a: Alerta) -> AlertaOut:
    est = session.get(Estudiante, a.estudiante_id)
    aula = session.get(Aula, est.aula_id) if est else None
    pred = session.get(Prediccion, a.prediccion_id) if a.prediccion_id else None
    return AlertaOut(
        **a.model_dump(exclude={"tutor_id"}),
        estudiante=f"{est.apellidos}, {est.nombres}" if est else None,
        aula=aula.nombre if aula else None, factores=pred.factores if pred else [],
    )


def _alerta_visible(session: Session, user: User, alerta_id: int) -> Alerta:
    alerta = session.get(Alerta, alerta_id)
    if not alerta or (user.rol == Rol.tutor and alerta.tutor_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta no encontrada")
    return alerta


@router.get("/alertas/{alerta_id}", response_model=AlertaOut, summary="RF-06 · Detalle de una alerta")
def detalle_alerta(
    alerta_id: int,
    user: User = Depends(require_role(Rol.tutor, Rol.director)),
    session: Session = Depends(get_session),
):
    return _alerta_out(session, _alerta_visible(session, user, alerta_id))


@router.patch("/alertas/{alerta_id}/leer", response_model=AlertaOut)
def marcar_leida(
    alerta_id: int,
    user: User = Depends(require_role(Rol.tutor, Rol.director)),
    session: Session = Depends(get_session),
):
    alerta = _alerta_visible(session, user, alerta_id)
    alerta.leida = True
    session.add(alerta)
    session.commit()
    session.refresh(alerta)
    return _alerta_out(session, alerta)


@router.get("/reportes/aula/{aula_id}/pdf", summary="RF-09 · Reporte consolidado en PDF")
def reporte_pdf(
    aula_id: int,
    user: User = Depends(require_role(Rol.director, Rol.tutor)),
    session: Session = Depends(get_session),
):
    aula = verificar_aula(session, user, aula_id)
    colegio = session.get(Colegio, aula.colegio_id)
    filas = []
    for est in session.exec(select(Estudiante).where(Estudiante.aula_id == aula.id).order_by(Estudiante.apellidos)):
        promedio = session.exec(select(func.avg(Nota.valor)).where(Nota.estudiante_id == est.id)).one()
        faltas = session.exec(
            select(func.count()).select_from(Asistencia)
            .where(Asistencia.estudiante_id == est.id, Asistencia.presente == False)  # noqa: E712
        ).one()
        pred = ultima_prediccion(session, est.id)
        filas.append({
            "codigo": est.codigo, "nombre": f"{est.apellidos}, {est.nombres}",
            "promedio": float(promedio) if promedio is not None else None, "inasistencias": faltas,
            "riesgo": pred.riesgo.value if pred else None, "probabilidad": pred.probabilidad if pred else None,
        })
    auditar(session, user, "exportar_pdf", f"aula:{aula.id}")
    pdf = reporte_aula_pdf(colegio.nombre if colegio else "", aula.nombre, filas)
    archivo = re.sub(r"[^A-Za-z0-9]+", "-", aula.nombre).strip("-").lower() or str(aula.id)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="reporte-aula-{archivo}.pdf"'})


@router.get(
    "/modelo", response_model=ModeloOut,
    summary="Ficha del modelo publicado: versión, métricas de prueba, matriz de confusión e importancia de variables",
)
def ficha_modelo(_: User = Depends(require_role(Rol.director, Rol.analista))):
    return a_modelo_out(ml_client.info_modelo())


@router.get("/config/riesgo", response_model=ConfigRiesgoIO)
def leer_config(
    _: User = Depends(require_role(Rol.analista, Rol.director)), session: Session = Depends(get_session)
):
    c = obtener_config(session)
    return ConfigRiesgoIO(umbral_amarillo=c.umbral_amarillo, umbral_rojo=c.umbral_rojo)


@router.put("/config/riesgo", response_model=ConfigRiesgoIO, summary="RF-10 · Configurar umbrales")
def actualizar_config(
    data: ConfigRiesgoIO, _: User = Depends(require_role(Rol.analista)), session: Session = Depends(get_session)
):
    c = obtener_config(session)
    c.umbral_amarillo, c.umbral_rojo = data.umbral_amarillo, data.umbral_rojo
    session.add(c)
    session.commit()
    return data
