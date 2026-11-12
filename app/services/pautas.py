"""Generador de pautas pedagógicas por reglas (sin IA generativa).

A cada factor de riesgo devuelto por el modelo se le asocian recomendaciones
redactadas en lenguaje claro para los padres. El equipo pedagógico puede
editar este diccionario sin tocar el resto del código.
"""

PAUTAS: dict[str, list[str]] = {
    "promedio": [
        "Revise semanalmente con su hijo(a) las notas publicadas y conversen sobre los cursos con menor rendimiento.",
        "Establezca un horario fijo de estudio de al menos 1 hora diaria, en un lugar tranquilo y sin distracciones.",
    ],
    "inasistencias": [
        "Asegure la asistencia diaria: cada falta implica contenidos que luego cuesta recuperar.",
        "Si hay una falta justificada, coordine con el tutor para obtener las tareas y materiales del día.",
    ],
    "conducta": [
        "Converse con su hijo(a) sobre las normas de convivencia del aula y refuerce positivamente los avances.",
        "Solicite una reunión con el tutor para acordar estrategias conjuntas entre casa y colegio.",
    ],
    "horas_estudio": [
        "Aumente gradualmente el tiempo de estudio en casa (por ejemplo, 15 minutos más cada semana).",
        "Use la técnica de bloques: 25 minutos de estudio y 5 de descanso.",
    ],
    "nivel_edu_padres": [
        "Aunque no domine los temas, acompañe a su hijo(a): pregúntele qué aprendió y pídale que se lo explique.",
        "Consulte al tutor por los espacios de reforzamiento que ofrece el colegio.",
    ],
    "acceso_tecnologia": [
        "Si no cuenta con computadora o internet, consulte al colegio por el uso del laboratorio o la biblioteca.",
    ],
    "tiempo_disponible_padres": [
        "Reserve al menos 10 minutos al día para revisar la agenda y las tareas de su hijo(a).",
        "Si su horario es limitado, designe a un familiar de confianza para acompañar el estudio.",
    ],
    "comunicacion_familiar": [
        "Genere un momento diario de conversación sin pantallas para hablar sobre el día en el colegio.",
        "Muestre interés por sus logros, no solo por sus notas.",
    ],
    "cursos_desaprobados": [
        "Priorice el repaso de los cursos desaprobados antes de las próximas evaluaciones (revise el calendario).",
        "Pregunte al docente del curso qué temas debe reforzar y con qué materiales.",
    ],
    "tareas_entregadas_pct": [
        "Revise diariamente la agenda o plataforma para verificar que las tareas se entreguen a tiempo.",
        "Ayude a su hijo(a) a organizar las tareas por fecha de entrega en un calendario visible.",
    ],
}

FACTOR_LEGIBLE: dict[str, str] = {
    "promedio": "promedio bajo",
    "inasistencias": "inasistencias",
    "conducta": "conducta",
    "horas_estudio": "pocas horas de estudio",
    "nivel_edu_padres": "nivel educativo de los padres",
    "acceso_tecnologia": "acceso a tecnología",
    "tiempo_disponible_padres": "poco tiempo de acompañamiento",
    "comunicacion_familiar": "comunicación familiar",
    "cursos_desaprobados": "cursos desaprobados",
    "tareas_entregadas_pct": "tareas no entregadas",
}

GENERICA ="Mantenga comunicación constante con el tutor y revise el avance de su hijo(a) cada semana."


def generar_pautas(factores: list[str], riesgo: str) -> list[tuple[str, str]]:
    """Devuelve [(factor, texto)]. En riesgo verde solo una pauta de refuerzo."""
    if riesgo == "verde":
        return [("general", "¡Buen desempeño! Siga acompañando el estudio diario para mantener los logros.")]
    pautas: list[tuple[str, str]] = []
    for factor in factores:
        textos = PAUTAS.get(factor, [GENERICA])
        cantidad = 2 if riesgo == "rojo" else 1
        pautas.extend((factor, t) for t in textos[:cantidad])
    return pautas or [("general", GENERICA)]
