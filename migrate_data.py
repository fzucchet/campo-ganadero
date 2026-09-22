"""
Script de migración de datos iniciales desde los cuadros Excel.
Ejecutar una sola vez: python3 migrate_data.py
"""
import sys
sys.path.insert(0, ".")

from datetime import date
from database.connection import get_engine, init_db
from database.models import Venta, Mortandad, TrabajoCorral
from sqlalchemy.orm import sessionmaker

init_db()
engine = get_engine()
Session = sessionmaker(bind=engine)
db = Session()


# ── 1. VENTAS / CARGAS ────────────────────────────────────────────────────────
ventas = [
    Venta(fecha=date(2026, 1,  6), categoria="terneras", cantidad=45,  kgs=None,  precio_total=69910893.6,  notas=None),
    Venta(fecha=date(2026, 2, 17), categoria="terneros", cantidad=100, kgs=None,  precio_total=104866340.4, notas=None),
    Venta(fecha=date(2026, 3,  2), categoria="vacas",    cantidad=8,   kgs=3625,  precio_total=9986875,     notas=None),
    Venta(fecha=date(2026, 3, 11), categoria="vacas",    cantidad=8,   kgs=3642,  precio_total=10033710,    notas=None),
    # 28/04 era lote mixto: 30 novillos + 7 vacas, precio total del lote
    Venta(fecha=date(2026, 4, 28), categoria="novillos", cantidad=30,  kgs=None,  precio_total=60328541.32, notas="30 novillos + 7 vacas — precio total del lote"),
    Venta(fecha=date(2026, 4, 28), categoria="vacas",    cantidad=7,   kgs=None,  precio_total=0,           notas="Incluidas en venta del 28/04 (ver novillos)"),
    # 30/04 era lote mixto: 98 terneros + 32 terneras
    Venta(fecha=date(2026, 4, 30), categoria="terneros", cantidad=98,  kgs=17289, precio_total=125984462.8, notas="98 terneros + 32 terneras — precio total del lote"),
    Venta(fecha=date(2026, 4, 30), categoria="terneras", cantidad=32,  kgs=None,  precio_total=0,           notas="Incluidas en venta del 30/04 (ver terneros)"),
    Venta(fecha=date(2026, 6,  5), categoria="vacas",    cantidad=14,  kgs=6230,  precio_total=17755500,    notas=None),
    Venta(fecha=date(2026, 7,  2), categoria="vacas",    cantidad=10,  kgs=5019,  precio_total=13827345,    notas=None),
    Venta(fecha=date(2026, 8,  1), categoria="vacas",    cantidad=10,  kgs=4373,  precio_total=12047615,    notas=None),
]

# ── 2. MORTANDAD ──────────────────────────────────────────────────────────────
mortandad = [
    Mortandad(fecha=date(2026, 5,  8), categoria="ternera", descripcion="Renga del 64",                     numero_caravana=64,  potrero=None),
    Mortandad(fecha=date(2026, 6, 18), categoria="ternera", descripcion="64 ternero sano",                  numero_caravana=64,  potrero=None),
    Mortandad(fecha=date(2026, 7,  3), categoria="ternero", descripcion="1 pero puede ser del 62",          numero_caravana=None, potrero="62"),
    Mortandad(fecha=date(2026, 7,  3), categoria="ternero", descripcion="Potrero 62",                       numero_caravana=None, potrero="62"),
    Mortandad(fecha=date(2026, 7, 10), categoria="ternero", descripcion="Tacuruzal",                        numero_caravana=None, potrero="Tacuruzal"),
    Mortandad(fecha=date(2026, 7, 10), categoria="vaca",    descripcion="Tacuruzal — mamá del ternero",     numero_caravana=None, potrero="Tacuruzal"),
    Mortandad(fecha=date(2026, 7, 24), categoria="vaca",    descripcion="Tacuruzal — hinchada sin cuervos", numero_caravana=None, potrero="Tacuruzal"),
    Mortandad(fecha=date(2026, 8,  2), categoria="ternero", descripcion="Potrero 63",                       numero_caravana=None, potrero="63"),
    Mortandad(fecha=date(2026, 8,  2), categoria="ternero", descripcion="Útero dado vuelta",                numero_caravana=None, potrero=None),
    Mortandad(fecha=date(2026, 8,  7), categoria="ternero", descripcion="Tacuruzal",                        numero_caravana=None, potrero="Tacuruzal"),
    Mortandad(fecha=date(2026, 8, 15), categoria="vaca",    descripcion="61 — baya vieja",                  numero_caravana=None, potrero="61"),
    Mortandad(fecha=date(2026, 8, 19), categoria="vaca",    descripcion="En el 2 — ternero también",        numero_caravana=None, potrero="2"),
    Mortandad(fecha=date(2026, 8, 23), categoria="vaca",    descripcion="Tacuruzal",                        numero_caravana=None, potrero="Tacuruzal"),
    Mortandad(fecha=date(2026, 8, 23), categoria="vaca",    descripcion="Dada vuelta útero",                numero_caravana=None, potrero=None),
    Mortandad(fecha=date(2026, 8, 28), categoria="ternero", descripcion="Potrero 62",                       numero_caravana=None, potrero="62"),
]

# ── 3. TRABAJOS A CORRAL ──────────────────────────────────────────────────────
trabajos = [
    TrabajoCorral(
        fecha=date(2026, 3, 27), tipo_trabajo="tactos / diagnóstico de preñez",
        animales="562 tactos: 111 vaquillas preñadas, 19 vacías",
        resultado="322 vacas preñadas y 110 vacas vacías",
    ),
    TrabajoCorral(
        fecha=date(2026, 3, 27), tipo_trabajo="aftosa",
        animales="562 vacas, 73 machos, 15 hembras y 27 novillos",
    ),
    TrabajoCorral(
        fecha=date(2026, 3, 31), tipo_trabajo="aftosa",
        animales="37 vacas, 30 toros, 6 machos, 3 hembras, 1 novillo",
    ),
    TrabajoCorral(
        fecha=date(2026, 4, 10), tipo_trabajo="vitamina + cobre + ricobendazol",
        animales="205 terneras + 36 vaquillas espera",
    ),
    TrabajoCorral(
        fecha=date(2026, 4, 10), tipo_trabajo="vitamina + ivermectina",
        animales="61 aptas",
    ),
    TrabajoCorral(
        fecha=date(2026, 4, 10), tipo_trabajo="tactos / diagnóstico de preñez",
        animales="195 vacas preñadas + 10 con cría + 11 vacías",
        resultado="Espera 36 + 41 Preñadas + 61 Aptas Vaquillas",
    ),
    TrabajoCorral(
        fecha=date(2026, 4, 10), tipo_trabajo="aftosa",
        animales="205 terneras + 138 vaquillas + 216 vacas",
    ),
    TrabajoCorral(
        fecha=date(2026, 4, 16), tipo_trabajo="aftosa",
        animales="18 machos + 21 hembras + 91 vacas laguna",
        resultado="59 preñadas + 7 rechazo + 25 vacías",
    ),
    TrabajoCorral(
        fecha=date(2026, 5, 19), tipo_trabajo="pour on",
        animales="86 vacas y 21 terneras — laguna",
    ),
    TrabajoCorral(
        fecha=date(2026, 5, 18), tipo_trabajo="entrada de toros",
        animales="25 toros al potrero 63",
    ),
    TrabajoCorral(
        fecha=date(2026, 6,  2), tipo_trabajo="pesaje",
        animales="203 vaquillas carimbo 4",
        resultado="48508 kgs totales. 9356 kg de 28 vaquillas espera que fueron al rodeo de otoño",
        notas="pesaje de vaquillas y descorne",
    ),
    TrabajoCorral(
        fecha=date(2026, 6, 17), tipo_trabajo="aparte / separación",
        animales="90 vacas y 7 con cría al corral",
        resultado="30964 kgs de 168 terneras. Distribución: 129 al 2, 100 al 63, 100 al 62, 183 al 1",
        notas="aparte vacas preñadas y vacías + destete",
    ),
    TrabajoCorral(
        fecha=date(2026, 7,  7), tipo_trabajo="ricobendazol + cobre",
        animales="198 terneras destete",
        notas="también mancha",
    ),
    TrabajoCorral(
        fecha=date(2026, 7,  8), tipo_trabajo="pesaje",
        animales="206 vaquillas",
        resultado="53309 kg de 206 vaquillas",
        notas="ricobendazol + pesaje vaquillas",
    ),
    TrabajoCorral(
        fecha=date(2026, 7, 15), tipo_trabajo="aparte / separación",
        animales="102 al potrero del corral, 7 destetes, 17 vacas con cría al Tacuruzal, 2 vacas viejas rechazo",
    ),
    TrabajoCorral(
        fecha=date(2026, 7, 21), tipo_trabajo="pesaje",
        animales="214 terneras",
        resultado="41217 kg de 214 terneras",
    ),
    TrabajoCorral(
        fecha=date(2026, 8, 27), tipo_trabajo="ricobendazol + suplenut",
        animales="201 vaquillas",
        resultado="58651 kg de 201 vaquillas — pesaje de las chicas: 77 x 19165 kg",
    ),
    TrabajoCorral(
        fecha=date(2026, 8, 27), tipo_trabajo="ricobendazol + cobre",
        animales="7 rechazos + 81 preñadas + 4 descarte con problemas + 74 vacías + 6 cut",
    ),
]

# ── Insertar en la base de datos ──────────────────────────────────────────────
try:
    db.add_all(ventas)
    db.add_all(mortandad)
    db.add_all(trabajos)
    db.commit()
    print(f"✅ Migración completada:")
    print(f"   - {len(ventas)} ventas")
    print(f"   - {len(mortandad)} registros de mortandad")
    print(f"   - {len(trabajos)} trabajos a corral")
except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
finally:
    db.close()
