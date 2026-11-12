"""Arma el vector de variables que espera edutrack-ml (ver ml-service/app/features.py)."""

from sqlmodel import Session, func, select

from app.models import Asistencia, Conducta, EncuestaSociofamiliar, Nota, Tarea

# Valores neutros cuando el apoderado aún no respondió la encuesta
POR_DEFECTO_ENCUESTA = {
    "horas_estudio": 4.0,
    "nivel_edu_padres": 2,
    "acceso_tecnologia": 1,
    "tiempo_disponible_padres": 2,
    "comunicacion_familiar": 2,
}


def construir_features(session: Session, estudiante_id: int, bimestre: int) -> dict | None:
    notas = list(session.exec(
        select(Nota.valor).where(Nota.estudiante_id == estudiante_id, Nota.bimestre == bimestre)
    ))
    if not notas:
        return None  # sin notas no se puede predecir

    inasistencias = session.exec(
        select(func.count()).select_from(Asistencia)
        .where(Asistencia.estudiante_id == estudiante_id, Asistencia.presente == False)  # noqa: E712
    ).one()

    conducta = session.exec(
        select(Conducta.valor)
        .where(Conducta.estudiante_id == estudiante_id, Conducta.bimestre == bimestre)
        .order_by(Conducta.id.desc())
    ).first() or 1

    tareas = list(session.exec(select(Tarea.entregada).where(Tarea.estudiante_id == estudiante_id)))
    tareas_pct = sum(tareas) / len(tareas) if tareas else 1.0

    encuesta = session.exec(
        select(EncuestaSociofamiliar)
        .where(EncuestaSociofamiliar.estudiante_id == estudiante_id)
        .order_by(EncuestaSociofamiliar.fecha.desc())
    ).first()
    socio = POR_DEFECTO_ENCUESTA if encuesta is None else {
        "horas_estudio": encuesta.horas_estudio,
        "nivel_edu_padres": encuesta.nivel_edu_padres,
        "acceso_tecnologia": int(encuesta.acceso_tecnologia),
        "tiempo_disponible_padres": encuesta.tiempo_disponible_padres,
        "comunicacion_familiar": encuesta.comunicacion_familiar,
    }

    return {
        "promedio": round(sum(notas) / len(notas), 2),
        "inasistencias": inasistencias,
        "conducta": conducta,
        "cursos_desaprobados": sum(1 for n in notas if n < 11),
        "tareas_entregadas_pct": round(tareas_pct, 3),
        **socio,
    }
