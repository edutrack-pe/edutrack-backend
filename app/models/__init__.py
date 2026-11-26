"""Modelo de datos de EduTrack (SQLModel → MySQL)."""

from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Rol(str, Enum):
    director = "director"
    docente = "docente"
    tutor = "tutor"
    padre = "padre"
    analista = "analista"


class Riesgo(str, Enum):
    verde = "verde"
    amarillo = "amarillo"
    rojo = "rojo"


# ---------- Usuarios y estructura institucional ----------

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=120)
    nombre: str = Field(max_length=120)
    hashed_password: str = Field(max_length=255)
    rol: Rol
    activo: bool = True


class Colegio(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=150)


class Aula(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=50)  # p. ej. "3° A"
    grado: int = Field(ge=1, le=5, index=True)  # 1.° a 5.° de secundaria
    seccion: str = Field(default="A", max_length=5)
    colegio_id: int = Field(foreign_key="colegio.id")
    tutor_id: int | None = Field(default=None, foreign_key="user.id")


class Estudiante(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(index=True, unique=True, max_length=20)
    nombres: str = Field(max_length=100)
    apellidos: str = Field(max_length=100)
    aula_id: int = Field(foreign_key="aula.id", index=True)
    apoderado_id: int | None = Field(default=None, foreign_key="user.id")


class Curso(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=80)
    aula_id: int = Field(foreign_key="aula.id", index=True)
    docente_id: int | None = Field(default=None, foreign_key="user.id")


# ---------- Datos académicos ----------

class Nota(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("estudiante_id", "curso_id", "bimestre", name="uq_nota_estudiante_curso_bimestre"),)

    id: int | None = Field(default=None, primary_key=True)
    estudiante_id: int = Field(foreign_key="estudiante.id", index=True)
    curso_id: int = Field(foreign_key="curso.id", index=True)
    bimestre: int = Field(ge=1, le=4)
    valor: float = Field(ge=0, le=20)


class Asistencia(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("estudiante_id", "fecha", name="uq_asistencia_estudiante_fecha"),)

    id: int | None = Field(default=None, primary_key=True)
    estudiante_id: int = Field(foreign_key="estudiante.id", index=True)
    fecha: date
    presente: bool = True


class Conducta(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("estudiante_id", "bimestre", name="uq_conducta_estudiante_bimestre"),)

    id: int | None = Field(default=None, primary_key=True)
    estudiante_id: int = Field(foreign_key="estudiante.id", index=True)
    bimestre: int = Field(ge=1, le=4)
    valor: int = Field(ge=1, le=3)  # 1 buena, 2 regular, 3 mala
    observacion: str | None = Field(default=None, max_length=255)


class Tarea(SQLModel, table=True):
    """Trazabilidad de tareas: una fila por tarea asignada a un estudiante."""

    id: int | None = Field(default=None, primary_key=True)
    estudiante_id: int = Field(foreign_key="estudiante.id", index=True)
    curso_id: int = Field(foreign_key="curso.id")
    titulo: str = Field(max_length=150)
    fecha_entrega: date
    entregada: bool = False


class EncuestaSociofamiliar(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    estudiante_id: int = Field(foreign_key="estudiante.id", index=True)
    horas_estudio: float = Field(ge=0, le=60)
    nivel_edu_padres: int = Field(ge=1, le=3)
    acceso_tecnologia: bool
    tiempo_disponible_padres: int = Field(ge=1, le=3)
    comunicacion_familiar: int = Field(ge=1, le=3)
    fecha: datetime = Field(default_factory=ahora)


# ---------- Riesgo, alertas y tutoría ----------

class Prediccion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    estudiante_id: int = Field(foreign_key="estudiante.id", index=True)
    bimestre: int
    riesgo: Riesgo
    probabilidad: float
    factores: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    modelo_version: str | None = Field(default=None, max_length=40)
    fecha: datetime = Field(default_factory=ahora, index=True)


class Pauta(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    prediccion_id: int = Field(foreign_key="prediccion.id", index=True)
    estudiante_id: int = Field(foreign_key="estudiante.id", index=True)
    factor: str = Field(max_length=60)
    texto: str = Field(max_length=500)


class Alerta(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    estudiante_id: int = Field(foreign_key="estudiante.id", index=True)
    prediccion_id: int | None = Field(default=None, foreign_key="prediccion.id")
    tutor_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    riesgo: Riesgo = Riesgo.rojo
    probabilidad: float | None = None
    mensaje: str = Field(max_length=300)
    leida: bool = False
    fecha: datetime = Field(default_factory=ahora)


class ActaTutoria(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    estudiante_id: int = Field(foreign_key="estudiante.id", index=True)
    tutor_id: int = Field(foreign_key="user.id")
    fecha: date
    acuerdos: str = Field(max_length=1000)
    compromisos: str | None = Field(default=None, max_length=1000)


class EventoCalendario(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    aula_id: int = Field(foreign_key="aula.id", index=True)
    curso_id: int | None = Field(default=None, foreign_key="curso.id")
    titulo: str = Field(max_length=150)
    fecha: date


class ConfigRiesgo(SQLModel, table=True):
    id: int | None = Field(default=1, primary_key=True)
    umbral_amarillo: float = 0.4
    umbral_rojo: float = 0.7


class AuditLog(SQLModel, table=True):
    """Registro de accesos a datos de menores (Ley N° 29733)."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    accion: str = Field(max_length=50)
    recurso: str = Field(max_length=100)
    fecha: datetime = Field(default_factory=ahora)
