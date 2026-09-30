"""
Migra TODOS los datos de la base SQLite local (campo.db) a una base PostgreSQL.

Uso:
    export TARGET_DATABASE_URL="postgresql://user:pass@host:port/db"
    python migrate_sqlite_to_postgres.py

Opcional:
    export SOURCE_DATABASE_URL="sqlite:///campo.db"   # por defecto ya es este

El script preserva los IDs, respeta el orden de las foreign keys y, al
terminar, reajusta las secuencias de PostgreSQL para que los próximos
inserts no colisionen. Es idempotente sobre tablas vacías: si la tabla
destino ya tiene filas, la saltea para no duplicar.
"""
import os
import sys

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, ".")

from database.connection import Base  # noqa: E402
from database import models as m  # noqa: E402

# Orden de copia: primero las tablas sin dependencias, luego las que tienen FKs.
MODELS_EN_ORDEN = [
    m.Potrero,
    m.TrabajoCorral,
    m.Venta,
    m.Mortandad,
    m.TipoTrabajoCatalogo,
    m.Gasto,
    m.MovimientoInventario,
    m.Reproduccion,
    m.IndiceReproductivo,
    m.AsignacionPotrero,       # depende de potreros
    m.MovimientoPotrero,       # depende de potreros y trabajos_corral
]


def _normalizar_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def main() -> None:
    source_url = _normalizar_url(os.getenv("SOURCE_DATABASE_URL", "sqlite:///campo.db"))
    target_url = os.getenv("TARGET_DATABASE_URL", "")

    if not target_url:
        print("❌ Falta la variable TARGET_DATABASE_URL con la URL del PostgreSQL destino.")
        sys.exit(1)
    target_url = _normalizar_url(target_url)

    print(f"Origen : {source_url}")
    print(f"Destino: {target_url.split('@')[-1]}")  # no imprime credenciales

    src_engine = create_engine(
        source_url,
        connect_args={"check_same_thread": False} if source_url.startswith("sqlite") else {},
    )
    tgt_engine = create_engine(target_url)

    SrcSession = sessionmaker(bind=src_engine)
    TgtSession = sessionmaker(bind=tgt_engine)
    src = SrcSession()
    tgt = TgtSession()

    # Crear las tablas en el destino si no existen.
    Base.metadata.create_all(bind=tgt_engine)

    total = 0
    try:
        for model in MODELS_EN_ORDEN:
            tabla = model.__tablename__
            existentes = tgt.query(func.count()).select_from(model).scalar()
            if existentes:
                print(f"⏭️  {tabla}: el destino ya tiene {existentes} filas, se saltea.")
                continue

            filas = src.query(model).all()
            if not filas:
                print(f"·  {tabla}: sin datos en el origen.")
                continue

            columnas = [c.name for c in model.__table__.columns]
            for fila in filas:
                datos = {col: getattr(fila, col) for col in columnas}
                tgt.add(model(**datos))
            tgt.commit()
            print(f"✅ {tabla}: {len(filas)} filas copiadas.")
            total += len(filas)

        # Reajustar las secuencias en PostgreSQL para el próximo id.
        if tgt_engine.dialect.name == "postgresql":
            for model in MODELS_EN_ORDEN:
                tabla = model.__tablename__
                tgt.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {tabla}), 1))"
                ))
            tgt.commit()
            print("🔧 Secuencias de PostgreSQL reajustadas.")

        print(f"\n🎉 Migración completada: {total} filas en total.")
    except Exception as e:
        tgt.rollback()
        print(f"❌ Error durante la migración: {e}")
        sys.exit(1)
    finally:
        src.close()
        tgt.close()


if __name__ == "__main__":
    main()
