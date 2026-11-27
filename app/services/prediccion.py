"""Orquesta la predicción (HU04): features → microservicio ML → Prediccion + Pautas + Alertas (HU06)."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Alerta, Aula, ConfigRiesgo, Estudiante, Pauta, Prediccion, Riesgo
from app.services import ml_client
from app.services.features import construir_features
from app.services.pautas import FACTOR_LEGIBLE, generar_pautas

DATOS_INSUFICIENTES = "Datos insuficientes: registre las calificaciones del bimestre actual"


def obtener_config(session: Session) -> ConfigRiesgo:
    config = session.get(ConfigRiesgo, 1)
    if not config:
        config = ConfigRiesgo(id=1)
        session.add(config)
        session.commit()
        session.refresh(config)
    return config


def _registrar_alerta(session: Session, est: Estudiante, aula: Aula, pred: Prediccion) -> bool:
    """Crea la alerta de riesgo alto. Si el estudiante ya tiene una alerta sin leer, la actualiza
    en lugar de duplicarla. Devuelve True si se creó una alerta nueva."""
    factores = ", ".join(FACTOR_LEGIBLE.get(f, f) for f in pred.factores) or "sin factor dominante"
    # HU06: la frase inicial es la del criterio de aceptación; el detalle va después.
    mensaje = (f"El estudiante {est.nombres} {est.apellidos} ha ingresado a nivel de Riesgo Alto. "
               f"Aula {aula.nombre}, probabilidad {pred.probabilidad:.0%}. Factores: {factores}.")[:300]
    pendiente = session.exec(
        select(Alerta).where(Alerta.estudiante_id == est.id, Alerta.leida == False)  # noqa: E712
    ).first()
    if pendiente:
        pendiente.prediccion_id, pendiente.probabilidad, pendiente.mensaje = pred.id, pred.probabilidad, mensaje
        pendiente.tutor_id = aula.tutor_id
        session.add(pendiente)
        return False
    session.add(Alerta(estudiante_id=est.id, prediccion_id=pred.id, tutor_id=aula.tutor_id,
                       riesgo=Riesgo.rojo, probabilidad=pred.probabilidad, mensaje=mensaje))
    return True


def _predecir(session: Session, estudiantes: list[Estudiante], aulas: dict[int, Aula], bimestre: int) -> dict:
    config = obtener_config(session)
    por_id = {e.id: e for e in estudiantes}
    solicitudes, sin_datos = [], []
    for est in estudiantes:
        features = construir_features(session, est.id, bimestre)
        if features is None:
            sin_datos.append(est.codigo)
            continue
        solicitudes.append({
            "student_id": est.id, "features": features,
            "umbral_amarillo": config.umbral_amarillo, "umbral_rojo": config.umbral_rojo,
        })
    if not solicitudes:  # escenario 02 de HU04: no se llama al microservicio
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, DATOS_INSUFICIENTES)

    resultados = ml_client.predecir_lote(solicitudes)
    resumen = {r.value: 0 for r in Riesgo}
    alertas_nuevas = 0
    version = None
    for res in resultados:
        est = por_id[res["student_id"]]
        version = res.get("modelo_version")
        pred = Prediccion(
            estudiante_id=est.id, bimestre=bimestre, riesgo=Riesgo(res["riesgo"]),
            probabilidad=res["probabilidad"], factores=res["factores"], modelo_version=version,
        )
        session.add(pred)
        session.flush()
        for factor, texto in generar_pautas(res["factores"], res["riesgo"]):
            session.add(Pauta(prediccion_id=pred.id, estudiante_id=est.id, factor=factor, texto=texto))
        if pred.riesgo == Riesgo.rojo and _registrar_alerta(session, est, aulas[est.aula_id], pred):
            alertas_nuevas += 1
        resumen[pred.riesgo.value] += 1

    session.commit()
    return {"bimestre": bimestre, "procesados": len(resultados), "sin_datos": sin_datos,
            "resumen": resumen, "alertas_generadas": alertas_nuevas, "modelo_version": version}


def predecir_aula(session: Session, aula: Aula, bimestre: int) -> dict:
    estudiantes = list(session.exec(select(Estudiante).where(Estudiante.aula_id == aula.id)))
    return {"aula_id": aula.id, **_predecir(session, estudiantes, {aula.id: aula}, bimestre)}


def predecir_estudiante(session: Session, est: Estudiante, bimestre: int) -> Prediccion:
    _predecir(session, [est], {est.aula_id: session.get(Aula, est.aula_id)}, bimestre)
    return ultima_prediccion(session, est.id)


def ultima_prediccion(session: Session, estudiante_id: int) -> Prediccion | None:
    return session.exec(
        select(Prediccion).where(Prediccion.estudiante_id == estudiante_id)
        .order_by(Prediccion.fecha.desc(), Prediccion.id.desc())
    ).first()


def ultimas_predicciones(session: Session, estudiante_ids: list[int]) -> dict[int, Prediccion]:
    """Última predicción de varios estudiantes con una sola consulta (evita N+1 en dashboard y listas)."""
    if not estudiante_ids:
        return {}
    ultimas = (
        select(Prediccion.estudiante_id, func.max(Prediccion.id).label("max_id"))
        .where(Prediccion.estudiante_id.in_(estudiante_ids))
        .group_by(Prediccion.estudiante_id)
        .subquery()
    )
    filas = session.exec(select(Prediccion).join(ultimas, Prediccion.id == ultimas.c.max_id))
    return {p.estudiante_id: p for p in filas}
