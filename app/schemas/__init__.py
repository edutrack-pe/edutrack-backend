"""DTOs de entrada/salida de la API (contrato OpenAPI)."""

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models import Riesgo, Rol


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: Rol
    nombre: str


class UserOut(BaseModel):
    id: int
    email: str
    nombre: str
    rol: Rol


class AulaOut(BaseModel):
    id: int
    nombre: str
    grado: int
    tutor_id: int | None


class EstudianteIn(BaseModel):
    codigo: str
    nombres: str
    apellidos: str
    aula_id: int
    apoderado_id: int | None = None


class EstudianteOut(BaseModel):
    id: int
    codigo: str
    nombres: str
    apellidos: str
    aula_id: int
    riesgo: Riesgo | None = None
    probabilidad: float | None = None


class NotaIn(BaseModel):
    estudiante_id: int
    curso_id: int
    bimestre: int = Field(ge=1, le=4)
    valor: float = Field(ge=0, le=20)


class NotaOut(NotaIn):
    id: int
    curso: str | None = None


class AsistenciaIn(BaseModel):
    estudiante_id: int
    fecha: date
    presente: bool = True


class AsistenciaOut(AsistenciaIn):
    id: int


class EncuestaIn(BaseModel):
    estudiante_id: int
    horas_estudio: float = Field(ge=0, le=60)
    nivel_edu_padres: int = Field(ge=1, le=3)
    acceso_tecnologia: bool
    tiempo_disponible_padres: int = Field(ge=1, le=3)
    comunicacion_familiar: int = Field(ge=1, le=3)


class PautaOut(BaseModel):
    factor: str
    texto: str


class PrediccionOut(BaseModel):
    id: int
    estudiante_id: int
    bimestre: int
    riesgo: Riesgo
    probabilidad: float
    factores: list[str]
    fecha: datetime


class FichaEstudiante(BaseModel):
    estudiante: EstudianteOut
    aula: str
    notas: list[NotaOut]
    asistencias_total: int
    inasistencias: int
    tareas_entregadas_pct: float | None
    prediccion: PrediccionOut | None
    pautas: list[PautaOut]


class ResultadoPrediccionAula(BaseModel):
    aula_id: int
    bimestre: int
    procesados: int
    sin_datos: list[str]
    resumen: dict[str, int]


class ResumenAula(BaseModel):
    aula_id: int
    aula: str
    total: int
    verde: int
    amarillo: int
    rojo: int
    sin_calcular: int


class DashboardOut(BaseModel):
    total_estudiantes: int
    verde: int
    amarillo: int
    rojo: int
    sin_calcular: int
    aulas: list[ResumenAula]


class AlertaOut(BaseModel):
    id: int
    estudiante_id: int
    mensaje: str
    leida: bool
    fecha: datetime


class ActaIn(BaseModel):
    estudiante_id: int
    fecha: date
    acuerdos: str = Field(min_length=3, max_length=1000)
    compromisos: str | None = Field(default=None, max_length=1000)


class ActaOut(ActaIn):
    id: int
    tutor_id: int


class EventoIn(BaseModel):
    aula_id: int
    curso_id: int | None = None
    titulo: str
    fecha: date


class EventoOut(EventoIn):
    id: int
    dias_restantes: int | None = None


class ConfigRiesgoIO(BaseModel):
    umbral_amarillo: float = Field(ge=0, le=1)
    umbral_rojo: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validar(self) -> "ConfigRiesgoIO":
        if self.umbral_amarillo >= self.umbral_rojo:
            raise ValueError("umbral_amarillo debe ser menor que umbral_rojo")
        return self


class IngestaOut(BaseModel):
    insertados: int
    errores: list[str]
