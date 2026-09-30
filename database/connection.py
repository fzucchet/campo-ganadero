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
    # Railway provee postgres://, SQLAlchemy necesita postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
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


def _migrar_columnas(engine):
    """Agrega columnas nuevas a tablas existentes (migración liviana, idempotente)."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "ventas" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("ventas")]
        if "composicion" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE ventas ADD COLUMN composicion VARCHAR(255)"))
