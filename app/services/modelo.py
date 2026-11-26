"""Traduce la ficha del modelo que entrega edutrack-ml al contrato de la API (sin recalcular nada)."""

from app.schemas import ModeloOut

# Claves con las que ml-service reporta la sensibilidad al umbral de decisión.
_SENSIBILIDAD = ("con_umbral_sistema_0_4", "con_umbral_0_5", "con_umbral_alto_0_7")


def a_modelo_out(info: dict) -> ModeloOut:
    ev = info.get("evaluacion")
    evaluacion = None
    if ev:
        prueba = ev["prueba"]
        importancias = sorted(ev.get("importancia_variables", {}).items(), key=lambda kv: kv[1], reverse=True)
        vif = ev.get("vif") or {}
        evaluacion = {
            "datos": ev["datos"],
            "validacion_cruzada": ev["validacion_cruzada"],
            "prueba": {k: prueba[k] for k in ("umbral", "precision", "recall", "f1", "matriz_confusion", "auc_roc")},
            "sensibilidad_umbral": sorted((prueba[k] for k in _SENSIBILIDAD if k in prueba), key=lambda m: m["umbral"]),
            "importancia_variables": [{"variable": v, "importancia": i} for v, i in importancias],
            "variables_descartadas_vif": ev.get("variables_descartadas_vif", []),
            "vif_maximo": max(vif.values()) if vif else None,
            "mejores_hiperparametros": ev.get("mejores_hiperparametros", {}),
            "metas": ev["metas"],
            "cumple_rnf02": ev["cumple_rnf02"],
        }
    return ModeloOut(
        version=info["version"],
        fecha_entrenamiento=info.get("fecha_entrenamiento"),
        variables=info.get("variables_modelo", []),
        umbral_decision=info.get("umbral_decision"),
        evaluacion=evaluacion,
    )
