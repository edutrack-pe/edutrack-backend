"""La migración inicial crea el mismo esquema que los modelos y se puede revertir."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

import app.models  # noqa: F401
from app.core.config import get_settings


def test_upgrade_coincide_con_modelos_y_downgrade(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migra.db').as_posix()}"
    monkeypatch.setattr(get_settings(), "database_url", url)
    cfg = Config("alembic.ini")

    command.upgrade(cfg, "head")
    engine = create_engine(url)
    with engine.connect() as conn:
        diferencias = compare_metadata(MigrationContext.configure(conn), SQLModel.metadata)
    assert diferencias == []
    restricciones = {u["name"] for u in inspect(engine).get_unique_constraints("nota")}
    assert "uq_nota_estudiante_curso_bimestre" in restricciones

    command.downgrade(cfg, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()
