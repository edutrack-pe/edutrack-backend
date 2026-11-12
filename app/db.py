import logging
import time
from collections.abc import Generator

from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

logger = logging.getLogger("edutrack.db")

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)


def init_db(intentos: int = 30, espera: float = 2.0) -> None:
    """Crea las tablas si no existen (MVP). Para cambios de esquema usar Alembic.

    Reintenta mientras la base de datos arranca (MySQL en Docker o RDS).
    """
    import app.models  # noqa: F401  registra los modelos en SQLModel.metadata

    for intento in range(1, intentos + 1):
        try:
            SQLModel.metadata.create_all(engine)
            return
        except OperationalError:
            if intento == intentos:
                raise
            logger.warning("Base de datos no disponible (intento %s/%s); reintentando…", intento, intentos)
            time.sleep(espera)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
