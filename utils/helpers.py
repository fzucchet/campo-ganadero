import pandas as pd
from database.connection import get_session
from database.models import (
    Venta, Mortandad, TrabajoCorral, Gasto,
    MovimientoInventario, Reproduccion, Potrero, AsignacionPotrero,
    MovimientoPotrero, IndiceReproductivo, TipoTrabajoCatalogo,
)

# Orden de las categorías de trabajo a corral (etiqueta con emoji → nombre limpio)
CATEGORIAS_TRABAJO_ORDEN = [
    "Sanidad", "Reproducción / Servicio", "Manejo / Organización", "Otro",
]
CATEGORIAS_TRABAJO_EMOJI = {
    "Sanidad": "🩺 Sanidad",
    "Reproducción / Servicio": "🐂 Reproducción / Servicio",
    "Manejo / Organización": "📋 Manejo / Organización",
    "Otro": "🗂️ Otro",
}

# Semilla inicial del catálogo (se carga sólo si la tabla está vacía)
_CATALOGO_SEED = {
    "Sanidad": [
        "aftosa", "brucelosis", "mancha", "polibac",
        "vitaminas", "vitamina + cobre", "vitamina + cobre + ricobendazol",
        "vitamina + ivermectina", "ricobendazol", "ricobendazol + cobre",
        "ricobendazol + suplenut", "pour on",
    ],
    "Reproducción / Servicio": [
        "tactos / diagnóstico de preñez", "entrada de toros", "salida de toros",
    ],
    "Manejo / Organización": [
        "aparte / separación", "destete", "pesaje", "pesaje de vaquillas",
        "pesaje de terneras", "descorne", "carimbo / marcación", "castración",
    ],
}



def fmt_pesos(value) -> str:
    """Formatea un número como pesos argentinos."""
    if value is None:
        return "-"
    return f"${value:,.0f}".replace(",", ".")


def fmt_kgs(value) -> str:
    if value is None:
        return "-"
    return f"{value:,.0f} kg".replace(",", ".")


# ── Loaders ──────────────────────────────────────────────────────────────────

def load_ventas() -> pd.DataFrame:
    db = get_session()
    try:
        rows = db.query(Venta).order_by(Venta.fecha.desc()).all()
        return pd.DataFrame([{
            "ID": r.id, "Fecha": r.fecha, "Categoría": r.categoria,
            "Cantidad": r.cantidad, "Kgs": r.kgs,
            "Precio Total": r.precio_total, "Composición": r.composicion or "",
            "Notas": r.notas or "",
        } for r in rows])
    finally:
        db.close()


def load_mortandad() -> pd.DataFrame:
    db = get_session()
    try:
        rows = db.query(Mortandad).order_by(Mortandad.fecha.desc()).all()
        return pd.DataFrame([{
            "ID": r.id, "Fecha": r.fecha, "Categoría": r.categoria,
            "Descripción": r.descripcion or "",
            "Potrero": r.potrero or "",
        } for r in rows])
    finally:
        db.close()


def load_trabajos() -> pd.DataFrame:
    db = get_session()
    try:
        rows = db.query(TrabajoCorral).order_by(TrabajoCorral.fecha.desc()).all()
        return pd.DataFrame([{
            "ID": r.id, "Fecha": r.fecha, "Categoría": r.categoria or "Otro",
            "Tipo de Trabajo": r.tipo_trabajo,
            "Animales": r.animales or "", "Resultado": r.resultado or "",
            "Notas": r.notas or "",
        } for r in rows])
    finally:
        db.close()


def load_gastos() -> pd.DataFrame:
    db = get_session()
    try:
        rows = db.query(Gasto).order_by(Gasto.fecha.desc()).all()
        return pd.DataFrame([{
            "ID": r.id, "Fecha": r.fecha, "Tipo": r.tipo,
            "Descripción": r.descripcion or "", "Monto": r.monto,
            "Proveedor": r.proveedor or "", "Notas": r.notas or "",
        } for r in rows])
    finally:
        db.close()


def load_reproduccion() -> pd.DataFrame:
    db = get_session()
    try:
        rows = db.query(Reproduccion).order_by(Reproduccion.fecha.desc()).all()
        return pd.DataFrame([{
            "ID": r.id, "Fecha": r.fecha, "Tipo": r.tipo,
            "Total Animales": r.total_animales, "Preñadas": r.prenadas,
            "Vacías": r.vacias, "Terneros M": r.terneros_machos,
            "Terneras H": r.terneras_hembras, "Notas": r.notas or "",
        } for r in rows])
    finally:
        db.close()


def load_indices_reproductivos() -> pd.DataFrame:
    """Índices reproductivos por temporada con % preñez y % destete calculados."""
    orden_temp = {"Otoño": 0, "Primavera": 1}
    db = get_session()
    try:
        rows = db.query(IndiceReproductivo).all()
        data = []
        for r in rows:
            pct_prenez = (r.prenadas / r.total * 100) if r.total else None
            pct_destete = (r.destete / r.prenadas * 100) if (r.destete and r.prenadas) else None
            data.append({
                "ID": r.id,
                "Temporada": r.temporada,
                "Año": r.anio,
                "Etiqueta": f"{r.temporada} {r.anio}",
                "Total": r.total,
                "Preñadas": r.prenadas,
                "% Preñez": pct_prenez,
                "Destete": r.destete,
                "Muertos Parto-Destete": r.muertos_parto_destete,
                "% Destete": pct_destete,
                "Notas": r.notas or "",
                "_orden": r.anio * 10 + orden_temp.get(r.temporada, 2),
            })
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values("_orden").drop(columns="_orden").reset_index(drop=True)
        return df
    finally:
        db.close()


def load_potreros() -> pd.DataFrame:
    db = get_session()
    try:
        rows = db.query(Potrero).order_by(Potrero.nombre).all()
        return pd.DataFrame([{
            "ID": r.id, "Nombre": r.nombre, "Número": r.numero or "",
            "Hectáreas": r.hectareas, "Notas": r.notas or "",
        } for r in rows])
    finally:
        db.close()


def load_asignaciones() -> pd.DataFrame:
    db = get_session()
    try:
        rows = (
            db.query(AsignacionPotrero, Potrero.nombre.label("potrero_nombre"))
            .join(Potrero)
            .order_by(AsignacionPotrero.fecha_entrada.desc())
            .all()
        )
        return pd.DataFrame([{
            "ID": r.AsignacionPotrero.id,
            "Potrero": r.potrero_nombre,
            "Categoría": r.AsignacionPotrero.categoria,
            "Cantidad": r.AsignacionPotrero.cantidad,
            "Entrada": r.AsignacionPotrero.fecha_entrada,
            "Salida": r.AsignacionPotrero.fecha_salida,
            "Notas": r.AsignacionPotrero.notas or "",
        } for r in rows])
    finally:
        db.close()


def stock_por_potrero() -> pd.DataFrame:
    """Stock activo (sin fecha de salida) segmentado por potrero y categoría.

    Devuelve una tabla pivote: una fila por potrero, una columna por categoría
    con la cantidad de cabezas actualmente asignadas, más una columna 'Total'.
    """
    db = get_session()
    try:
        rows = (
            db.query(AsignacionPotrero, Potrero.nombre.label("potrero_nombre"))
            .join(Potrero)
            .filter(AsignacionPotrero.fecha_salida.is_(None))
            .all()
        )
    finally:
        db.close()

    if not rows:
        return pd.DataFrame()

    base = pd.DataFrame([{
        "Potrero": r.potrero_nombre,
        "Categoría": r.AsignacionPotrero.categoria,
        "Cantidad": r.AsignacionPotrero.cantidad,
    } for r in rows])

    pivote = base.pivot_table(
        index="Potrero", columns="Categoría", values="Cantidad",
        aggfunc="sum", fill_value=0,
    )
    pivote["Total"] = pivote.sum(axis=1)
    pivote = pivote.sort_values("Total", ascending=False).reset_index()
    pivote.columns.name = None
    return pivote


def load_movimientos_potrero() -> pd.DataFrame:
    """Historial de movimientos de lotes entre potreros."""
    from sqlalchemy.orm import aliased
    OrigenPot = aliased(Potrero)
    DestinoPot = aliased(Potrero)
    db = get_session()
    try:
        rows = (
            db.query(
                MovimientoPotrero,
                OrigenPot.nombre.label("origen_nombre"),
                DestinoPot.nombre.label("destino_nombre"),
            )
            .join(OrigenPot, MovimientoPotrero.origen_potrero_id == OrigenPot.id)
            .join(DestinoPot, MovimientoPotrero.destino_potrero_id == DestinoPot.id)
            .order_by(MovimientoPotrero.fecha.desc(), MovimientoPotrero.id.desc())
            .all()
        )
        data = []
        for r in rows:
            m = r.MovimientoPotrero
            trabajo_txt = ""
            if m.trabajo_corral_id and m.trabajo:
                trabajo_txt = f"{m.trabajo.fecha.strftime('%d/%m/%Y')} · {m.trabajo.tipo_trabajo}"
            data.append({
                "ID": m.id,
                "Fecha": m.fecha,
                "Origen": r.origen_nombre,
                "Destino": r.destino_nombre,
                "Categoría": m.categoria,
                "Cantidad": m.cantidad,
                "Tipo": m.tipo,
                "Trabajo de corral": trabajo_txt,
                "Notas": m.notas or "",
            })
        return pd.DataFrame(data)
    finally:
        db.close()


def registrar_movimiento_potrero(
    origen_id: int, destino_id: int, categoria: str, cantidad: int,
    fecha, tipo: str = "directo", trabajo_corral_id=None, notas: str | None = None,
) -> None:
    """Registra el movimiento de un lote de un potrero a otro.

    Consume las asignaciones activas de la categoría en el potrero de origen
    (FIFO por fecha de entrada), crea una asignación nueva en el destino y
    guarda el movimiento en el historial. Todo en una sola transacción.

    Lanza ValueError si no hay stock activo suficiente en el origen.
    """
    if origen_id == destino_id:
        raise ValueError("El potrero de origen y destino no pueden ser el mismo.")
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a cero.")

    db = get_session()
    try:
        activos = (
            db.query(AsignacionPotrero)
            .filter(
                AsignacionPotrero.potrero_id == origen_id,
                AsignacionPotrero.categoria == categoria,
                AsignacionPotrero.fecha_salida.is_(None),
            )
            .order_by(AsignacionPotrero.fecha_entrada.asc(), AsignacionPotrero.id.asc())
            .all()
        )
        disponible = sum(a.cantidad for a in activos)
        if cantidad > disponible:
            raise ValueError(
                f"Stock insuficiente: hay {disponible} {categoria} en el potrero de origen "
                f"y querés mover {cantidad}."
            )

        # Consumir del origen en orden FIFO
        restante = cantidad
        for a in activos:
            if restante <= 0:
                break
            if a.cantidad <= restante:
                a.fecha_salida = fecha       # el lote completo sale del origen
                restante -= a.cantidad
            else:
                a.cantidad -= restante        # sale sólo una parte; el resto queda
                restante = 0

        # Crear asignación en el destino
        db.add(AsignacionPotrero(
            potrero_id=destino_id,
            fecha_entrada=fecha,
            fecha_salida=None,
            categoria=categoria,
            cantidad=cantidad,
            notas=notas or None,
        ))

        # Registrar el movimiento en el historial
        db.add(MovimientoPotrero(
            fecha=fecha,
            origen_potrero_id=origen_id,
            destino_potrero_id=destino_id,
            categoria=categoria,
            cantidad=cantidad,
            tipo=tipo,
            trabajo_corral_id=trabajo_corral_id,
            notas=notas or None,
        ))

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def load_movimientos_inventario() -> pd.DataFrame:
    db = get_session()
    try:
        rows = db.query(MovimientoInventario).order_by(MovimientoInventario.fecha.desc()).all()
        return pd.DataFrame([{
            "ID": r.id, "Fecha": r.fecha, "Categoría": r.categoria,
            "Cantidad": r.cantidad, "Tipo": r.tipo_movimiento,
            "Monto": r.monto, "Notas": r.notas or "",
        } for r in rows])
    finally:
        db.close()


# ── Catálogo de tipos de trabajo a corral ─────────────────────────────────────

def seed_catalogo_tipos_si_vacio() -> None:
    """Carga los tipos iniciales sólo si el catálogo está vacío (idempotente)."""
    db = get_session()
    try:
        if db.query(TipoTrabajoCatalogo).count() > 0:
            return
        for categoria, nombres in _CATALOGO_SEED.items():
            for nombre in nombres:
                db.add(TipoTrabajoCatalogo(nombre=nombre, categoria=categoria, activo=True))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def load_catalogo_tipos() -> pd.DataFrame:
    """Todos los tipos del catálogo (para administrarlos)."""
    db = get_session()
    try:
        rows = (
            db.query(TipoTrabajoCatalogo)
            .order_by(TipoTrabajoCatalogo.categoria, TipoTrabajoCatalogo.nombre)
            .all()
        )
        return pd.DataFrame([{
            "ID": r.id, "Nombre": r.nombre, "Categoría": r.categoria,
            "Activo": bool(r.activo),
        } for r in rows])
    finally:
        db.close()


def get_tipos_por_categoria(solo_activos: bool = True) -> dict:
    """Devuelve {categoria: [nombres]} ordenado, para armar los checkboxes."""
    db = get_session()
    try:
        q = db.query(TipoTrabajoCatalogo)
        if solo_activos:
            q = q.filter(TipoTrabajoCatalogo.activo.is_(True))
        rows = q.order_by(TipoTrabajoCatalogo.nombre).all()
    finally:
        db.close()
    agrupado: dict = {}
    for r in rows:
        agrupado.setdefault(r.categoria, []).append(r.nombre)
    # Ordenar según el orden canónico de categorías
    ordenado = {cat: agrupado[cat] for cat in CATEGORIAS_TRABAJO_ORDEN if cat in agrupado}
    # Agregar cualquier categoría extra no prevista
    for cat, nombres in agrupado.items():
        if cat not in ordenado:
            ordenado[cat] = nombres
    return ordenado


def categoria_de_tipos(nombres: list) -> str:
    """Dada una lista de tipos elegidos, deriva la categoría (o 'Mixto')."""
    db = get_session()
    try:
        cats = set()
        for n in nombres:
            row = db.query(TipoTrabajoCatalogo).filter(TipoTrabajoCatalogo.nombre == n).first()
            cats.add(row.categoria if row else "Otro")
    finally:
        db.close()
    if not cats:
        return "Otro"
    if len(cats) == 1:
        return next(iter(cats))
    return "Mixto"

