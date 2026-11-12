"""Orquesta la predicción de un aula: features → ML → Prediccion + Pautas + Alertas."""

from sqlmodel import Session, select

from app.models import Alerta, Aula, ConfigRiesgo, Estudiante, Pauta, Prediccion, Riesgo
from app.services import ml_client
from app.services.features import construir_features
from app.services.pautas import generar_pautas


def obtener_config(session: Session) -> ConfigRiesgo:
    config = session.get(ConfigRiesgo, 1)
    if not config:
        config = ConfigRiesgo(id=1)
        session.add(config)
        session.commit()
        session.refresh(config)
    return config


def predecir_aula(session: Session, aula: Aula, bimestre: int) -> dict:
    config = obtener_config(session)
    estudiantes = {e.id: e for e in session.exec(select(Estudiante).where(Estudiante.aula_id == aula.id))}

    solicitudes, sin_datos = [], []
    for est in estudiantes.values():
        features = construir_features(session, est.id, bimestre)
        if features is None:
            sin_datos.append(est.codigo)
            continue
        solicitudes.append({
            "student_id": est.id,
            "features": features,
            "umbral_amarillo": config.umbral_amarillo,
            "umbral_rojo": config.umbral_rojo,
        })

    resultados = ml_client.predecir_lote(solicitudes)
    resumen = {r.value: 0 for r in Riesgo}

    for res in resultados:
        est = estudiantes[res["student_id"]]
        pred = Prediccion(
            estudiante_id=est.id, bimestre=bimestre, riesgo=Riesgo(res["riesgo"]),
            probabilidad=res["probabilidad"], factores=res["factores"],
        )
        session.add(pred)
        session.flush()  # obtiene pred.id
        for factor, texto in generar_pautas(res["factores"], res["riesgo"]):
            session.add(Pauta(prediccion_id=pred.id, estudiante_id=est.id, factor=factor, texto=texto))
        if pred.riesgo == Riesgo.rojo:
            session.add(Alerta(
                estudiante_id=est.id, tutor_id=aula.tutor_id,
                mensaje=f"{est.nombres} {est.apellidos} ({aula.nombre}) está en RIESGO ALTO "
                        f"({pred.probabilidad:.0%}). Factores: {', '.join(pred.factores)}.",
            ))
        resumen[pred.riesgo.value] += 1

    session.commit()
    return {"aula_id": aula.id, "bimestre": bimestre, "procesados": len(resultados),
            "sin_datos": sin_datos, "resumen": resumen}


def ultima_prediccion(session: Session, estudiante_id: int) -> Prediccion | None:
    return session.exec(
        select(Prediccion).where(Prediccion.estudiante_id == estudiante_id)
        .order_by(Prediccion.fecha.desc(), Prediccion.id.desc())
    ).first()
