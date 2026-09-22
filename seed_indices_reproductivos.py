"""
Carga del histórico de índices reproductivos por temporada.
Ejecutar: python3 seed_indices_reproductivos.py

Es idempotente: si una temporada ya existe (misma temporada + año), la saltea.
Los porcentajes NO se guardan; se calculan siempre a partir de los valores crudos.
"""
import sys
sys.path.insert(0, ".")

from database.connection import get_engine, init_db
from database.models import IndiceReproductivo
from sqlalchemy.orm import sessionmaker

# (temporada, año, total, preñadas, destete, muertos_parto_destete)
DATOS = [
    ("Otoño",     2005, 172,  87, None, None),
    ("Primavera", 2012, 390, 237, None, None),
    ("Otoño",     2012, 182, 112, None, None),
    ("Primavera", 2013, 313, 242,  204,   38),
    ("Otoño",     2013, 202, 136, None, None),
    ("Primavera", 2014, 363, 185, None, None),
    ("Otoño",     2015, 280, 138, None, None),
    ("Primavera", 2015, 313, 207, None, None),
    ("Primavera", 2016, 630, 424, None, None),
    ("Primavera", 2017, 588, 439, None, None),
    ("Primavera", 2018, 643, 359, None, None),
    ("Primavera", 2019, 669, 459, None, None),
    ("Primavera", 2020, 551, 420, None, None),
    ("Primavera", 2021, 726, 553, None, None),
    ("Primavera", 2022, 651, 468,  418,   50),
    ("Primavera", 2023, 834, 641,  608,   33),
    ("Primavera", 2024, 750, 431, None, None),
    ("Primavera", 2025, 869, 687, None, None),
]


def main() -> None:
    init_db()
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        insertados, saltados = 0, 0
        for temporada, anio, total, prenadas, destete, muertos in DATOS:
            existe = (
                db.query(IndiceReproductivo)
                .filter(
                    IndiceReproductivo.temporada == temporada,
                    IndiceReproductivo.anio == anio,
                )
                .first()
            )
            if existe:
                saltados += 1
                continue
            db.add(
                IndiceReproductivo(
                    temporada=temporada,
                    anio=anio,
                    total=total,
                    prenadas=prenadas,
                    destete=destete,
                    muertos_parto_destete=muertos,
                )
            )
            insertados += 1
        db.commit()
        print(f"✅ Índices reproductivos: {insertados} insertados, {saltados} ya existían.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error al cargar índices: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
