"""Conexión a la base de datos: argumentos por motor y TLS hacia MySQL."""

import os

import pytest
from sqlalchemy import create_engine, text

from app.core.config import Settings
from app.db import argumentos_conexion


def test_sqlite_permite_varios_hilos():
    assert argumentos_conexion(Settings(database_url="sqlite://")) == {"check_same_thread": False}


def test_mysql_sin_ca_no_fuerza_tls():
    assert argumentos_conexion(Settings(database_url="mysql+pymysql://u:c@h/db", database_ssl_ca="")) == {}


def test_mysql_con_ca_activa_tls_verificado():
    cfg = Settings(database_url="mysql+pymysql://u:c@h/db", database_ssl_ca="/certs/rds.pem")
    assert argumentos_conexion(cfg) == {"ssl": {"ca": "/certs/rds.pem", "check_hostname": True}}


@pytest.mark.skipif(not (os.getenv("TEST_DATABASE_URL") and os.getenv("TEST_DATABASE_SSL_CA")),
                    reason="Requiere un MySQL real: TEST_DATABASE_URL y TEST_DATABASE_SSL_CA")
def test_conexion_real_a_mysql_va_cifrada():
    cfg = Settings(database_url=os.environ["TEST_DATABASE_URL"], database_ssl_ca=os.environ["TEST_DATABASE_SSL_CA"],
                   database_ssl_verify_hostname=os.getenv("TEST_DATABASE_SSL_VERIFY_HOSTNAME", "true") == "true")
    engine = create_engine(cfg.database_url, connect_args=argumentos_conexion(cfg))
    with engine.connect() as con:
        cifrado = con.execute(text("SHOW SESSION STATUS LIKE 'Ssl_cipher'")).one()[1]
    engine.dispose()
    assert cifrado, "La conexión a MySQL no usa TLS"
