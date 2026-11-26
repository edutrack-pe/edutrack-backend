from contextlib import asynccontextmanager

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db import init_db
from app.routers import academico, auth, estudiantes, riesgo, tutoria


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="EduTrack API",
    description="API REST de seguimiento académico y alerta temprana del riesgo de desaprobación/deserción.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("edutrack.api")


@app.exception_handler(IntegrityError)
async def conflicto_de_integridad(_: Request, exc: IntegrityError) -> JSONResponse:
    """Una restricción de la base de datos (duplicado o referencia inválida) se informa como 409, sin detalles SQL."""
    logger.warning("Violación de integridad: %s", exc.orig)
    return JSONResponse(status_code=status.HTTP_409_CONFLICT,
                        content={"detail": "El registro ya existe o hace referencia a datos inexistentes"})


@app.exception_handler(Exception)
async def error_inesperado(_: Request, exc: Exception) -> JSONResponse:
    """Nunca se expone la traza al cliente; se registra en el log del servidor."""
    logger.exception("Error no controlado", exc_info=exc)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content={"detail": "Ocurrió un error interno. Intente nuevamente."})


for r in (auth, estudiantes, academico, riesgo, tutoria):
    app.include_router(r.router, prefix="/api")


@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}
