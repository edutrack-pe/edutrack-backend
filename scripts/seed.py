"""Carga datos de demostración: 1 colegio, 3 aulas, 90 estudiantes y 1 usuario por rol.

Uso:  python scripts/seed.py
La contraseña de todos los usuarios demo se toma de SEED_DEFAULT_PASSWORD (.env).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db import engine, init_db  # noqa: E402
from app.seed_data import USUARIOS, poblar  # noqa: E402


def main() -> None:
    password = get_settings().seed_default_password
    if len(password) < 8:
        sys.exit("Define SEED_DEFAULT_PASSWORD (mínimo 8 caracteres) en el archivo .env")
    init_db()
    with Session(engine) as session:
        print(poblar(session, password))
    print("Usuarios demo:", ", ".join(f"{e} ({r.value})" for e, _, r in USUARIOS))


if __name__ == "__main__":
    main()
