import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


@st.cache_resource
def get_engine():
    database_url = os.getenv("DATABASE_URL", "sqlite:///campo.db")
    # Normaliza a psycopg2 explícito (independiente del driver por defecto de SQLAlchemy).
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    from database import models as _  # noqa: F401 — registra los modelos con Base
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrar_columnas(engine)
    _normalizar_potreros_mortandad(engine)


def _migrar_columnas(engine):
    """Agrega columnas nuevas a tablas existentes (migración liviana, idempotente)."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "ventas" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("ventas")]
        if "composicion" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE ventas ADD COLUMN composicion VARCHAR(255)"))


def _normalizar_potreros_mortandad(engine):
    """Unifica los potreros de mortandad al nombre oficial registrado.

    Compara sin distinguir mayúsculas ni espacios y reescribe cada valor al
    nombre canónico de la tabla `potreros`. Idempotente: solo actualiza filas
    cuyo valor difiere del canónico.
    """
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    tablas = insp.get_table_names()
    if "potreros" not in tablas or "mortandad" not in tablas:
        return

    with engine.begin() as conn:
        canonicos = {}
        filas = conn.execute(text("SELECT nombre, numero FROM potreros")).all()
        # Primero por nombre (tiene prioridad), luego por número.
        for nombre, _numero in filas:
            if nombre and nombre.strip():
                canonicos[nombre.strip().lower()] = nombre
        for nombre, numero in filas:
            if not (nombre and nombre.strip() and numero):
                continue
            for parte in str(numero).split(","):
                clave = parte.strip().lower()
                if clave and clave not in canonicos:
                    canonicos[clave] = nombre
        if not canonicos:
            return
        valores = conn.execute(
            text("SELECT DISTINCT potrero FROM mortandad WHERE potrero IS NOT NULL")
        ).all()
        for (valor,) in valores:
            if not valor:
                continue
            canonico = canonicos.get(valor.strip().lower())
            if canonico and canonico != valor:
                conn.execute(
                    text("UPDATE mortandad SET potrero = :nuevo WHERE potrero = :viejo"),
                    {"nuevo": canonico, "viejo": valor},
                )
