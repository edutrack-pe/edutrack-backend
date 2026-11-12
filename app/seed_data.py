"""Datos de demostración (sintéticos, sin datos reales de menores)."""

import random
from datetime import date, timedelta

from sqlmodel import Session, select

from app.core.security import hash_password
from app.models import (
    Asistencia, Aula, Colegio, ConfigRiesgo, Conducta, Curso, EncuestaSociofamiliar, Estudiante,
    EventoCalendario, Nota, Rol, Tarea, User,
)

NOMBRES = ["Ana", "Luis", "María", "José", "Lucía", "Carlos", "Valeria", "Diego", "Camila", "Mateo",
           "Sofía", "Andrés", "Daniela", "Jorge", "Fernanda", "Renzo", "Alessandra", "Bruno", "Ximena", "Piero"]
APELLIDOS = ["Quispe", "Flores", "Rojas", "Huamán", "Mendoza", "Torres", "Vargas", "Castillo", "Ramos",
             "Chávez", "Díaz", "Gutiérrez", "Paredes", "Salazar", "Cruz", "Vega", "Ríos", "Campos"]
CURSOS = ["Matemática", "Comunicación", "Ciencia y Tecnología", "Inglés"]

USUARIOS = [
    ("director@edutrack.pe", "Dirección Académica", Rol.director),
    ("analista@edutrack.pe", "Analista Funcional", Rol.analista),
    ("tutor1@edutrack.pe", "Tutor 3° A", Rol.tutor),
    ("tutor2@edutrack.pe", "Tutor 3° B", Rol.tutor),
    ("tutor3@edutrack.pe", "Tutor 4° A", Rol.tutor),
    ("docente1@edutrack.pe", "Docente de Ciencias", Rol.docente),
    ("docente2@edutrack.pe", "Docente de Letras", Rol.docente),
    ("padre@edutrack.pe", "Apoderado Demo", Rol.padre),
]


def poblar(session: Session, password: str, alumnos_por_aula: int = 30, seed: int = 7) -> dict:
    if session.exec(select(User)).first():
        return {"mensaje": "La base de datos ya tiene datos; no se hizo nada."}

    rng = random.Random(seed)
    usuarios = {}
    hashed = hash_password(password)
    for email, nombre, rol in USUARIOS:
        u = User(email=email, nombre=nombre, hashed_password=hashed, rol=rol)
        session.add(u)
        usuarios[email] = u
    colegio = Colegio(nombre="I.E.P. Colegio Demo – UGEL 03")
    session.add(colegio)
    session.add(ConfigRiesgo(id=1))
    session.flush()

    aulas_def = [("3° A", 3, "tutor1@edutrack.pe"), ("3° B", 3, "tutor2@edutrack.pe"), ("4° A", 4, "tutor3@edutrack.pe")]
    hoy = date.today()
    inicio_bimestre = hoy - timedelta(days=40)
    contador = 0

    for nombre_aula, grado, tutor in aulas_def:
        aula = Aula(nombre=nombre_aula, grado=grado, colegio_id=colegio.id, tutor_id=usuarios[tutor].id)
        session.add(aula)
        session.flush()
        cursos = []
        for i, nombre_curso in enumerate(CURSOS):
            docente = usuarios["docente1@edutrack.pe" if i % 2 == 0 else "docente2@edutrack.pe"]
            c = Curso(nombre=nombre_curso, aula_id=aula.id, docente_id=docente.id)
            session.add(c)
            cursos.append(c)
        session.flush()

        for c in cursos:
            session.add(EventoCalendario(aula_id=aula.id, curso_id=c.id, titulo=f"Evaluación bimestral de {c.nombre}",
                                         fecha=hoy + timedelta(days=rng.randint(3, 25))))

        for _ in range(alumnos_por_aula):
            contador += 1
            perfil = rng.random()  # < 0.25 = perfil en riesgo
            base = rng.uniform(7, 11.5) if perfil < 0.25 else rng.uniform(11, 18)
            est = Estudiante(
                codigo=f"A{contador:04d}", nombres=rng.choice(NOMBRES),
                apellidos=f"{rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}", aula_id=aula.id,
                apoderado_id=usuarios["padre@edutrack.pe"].id if contador == 1 else None,
            )
            session.add(est)
            session.flush()

            for c in cursos:
                session.add(Nota(estudiante_id=est.id, curso_id=c.id, bimestre=1,
                                 valor=round(min(20, max(0, rng.gauss(base, 1.5))), 1)))
                for t in range(3):
                    session.add(Tarea(estudiante_id=est.id, curso_id=c.id, titulo=f"Tarea {t + 1} de {c.nombre}",
                                      fecha_entrega=inicio_bimestre + timedelta(days=10 * (t + 1)),
                                      entregada=rng.random() > (0.5 if perfil < 0.25 else 0.1)))
            prob_falta = 0.2 if perfil < 0.25 else 0.04
            for d in range(30):
                dia = inicio_bimestre + timedelta(days=d)
                if dia.weekday() < 5:
                    session.add(Asistencia(estudiante_id=est.id, fecha=dia, presente=rng.random() > prob_falta))
            session.add(Conducta(estudiante_id=est.id, bimestre=1,
                                 valor=rng.choice([2, 3]) if perfil < 0.25 and rng.random() < 0.5 else 1))
            if rng.random() < 0.8:  # 80 % de apoderados respondió la encuesta
                session.add(EncuestaSociofamiliar(
                    estudiante_id=est.id,
                    horas_estudio=round(rng.uniform(0, 3) if perfil < 0.25 else rng.uniform(3, 10), 1),
                    nivel_edu_padres=rng.choice([1, 2, 3]),
                    acceso_tecnologia=rng.random() > 0.2,
                    tiempo_disponible_padres=rng.choice([1, 2, 3]),
                    comunicacion_familiar=rng.choice([1, 2]) if perfil < 0.25 else rng.choice([2, 3]),
                ))

    session.commit()
    return {"usuarios": len(usuarios), "aulas": len(aulas_def), "estudiantes": contador}
