from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

for r in (auth, estudiantes, academico, riesgo, tutoria):
    app.include_router(r.router, prefix="/api")


@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}
