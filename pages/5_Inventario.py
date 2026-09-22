import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database.connection import get_session
from database.models import MovimientoInventario, Venta, Mortandad
from utils.auth import require_auth
from utils.helpers import fmt_pesos, load_movimientos_inventario
from utils.editor import editable_table

st.set_page_config(page_title="Inventario | Campo Ganadero", page_icon="📦", layout="wide")
require_auth()

CATEGORIAS = ["terneros", "terneras", "vacas", "novillos", "toros", "vaquillas", "bueyes"]
TIPOS_MOV = ["compra", "nacimiento", "destete", "ajuste de inventario", "otro ingreso"]

st.title("📦 Inventario de Hacienda")
st.markdown("Stock actual calculado automáticamente a partir de entradas, ventas y mortandad")
st.markdown("---")

# ── Stock calculado ───────────────────────────────────────────────────────────
st.subheader("Stock actual estimado")

db = get_session()
try:
    # Entradas: compras, nacimientos, etc.
    movs = db.query(MovimientoInventario).all()
    ventas = db.query(Venta).all()
    bajas = db.query(Mortandad).all()
finally:
    db.close()

stock: dict[str, int] = {c: 0 for c in CATEGORIAS}

for mov in movs:
    cat = mov.categoria.lower()
    if cat in stock:
        stock[cat] += mov.cantidad  # puede ser negativo para ajustes

for v in ventas:
    cat = v.categoria.lower()
    if cat in stock:
        stock[cat] -= v.cantidad

for b in bajas:
    cat = b.categoria.lower()
    # normalizar singular/plural
    if cat in ("ternero",):
        cat = "terneros"
    elif cat in ("ternera",):
        cat = "terneras"
    elif cat in ("vaca",):
        cat = "vacas"
    elif cat in ("toro",):
        cat = "toros"
    elif cat in ("novillo",):
        cat = "novillos"
    elif cat in ("vaquilla",):
        cat = "vaquillas"
    if cat in stock:
        stock[cat] -= 1

df_stock = pd.DataFrame(
    [(cat.capitalize(), cant) for cat, cant in stock.items()],
    columns=["Categoría", "Cabezas estimadas"],
)
df_stock = df_stock[df_stock["Cabezas estimadas"] != 0]

col_tab, col_graf = st.columns([1, 1])
with col_tab:
    st.dataframe(df_stock, use_container_width=True, hide_index=True)
    total = df_stock["Cabezas estimadas"].sum()
    st.metric("Total general", f"{total} cabezas")
    st.caption("⚠️ Este stock es una estimación. Usá 'ajuste de inventario' para corregir diferencias.")

with col_graf:
    if not df_stock.empty:
        fig = px.bar(df_stock, x="Categoría", y="Cabezas estimadas",
                     color="Categoría",
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Registrar movimiento ──────────────────────────────────────────────────────
with st.expander("➕ Registrar entrada / ajuste de inventario", expanded=False):
    st.caption("Usá esto para registrar compras, nacimientos o correcciones manuales del stock.")
    with st.form("form_inv", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input("Fecha", value=date.today())
            tipo_mov = st.selectbox("Tipo de movimiento", TIPOS_MOV)
        with c2:
            categoria = st.selectbox("Categoría", CATEGORIAS)
            cantidad = st.number_input(
                "Cantidad (+entrada / −ajuste)", step=1, value=0,
                help="Positivo para sumar al stock, negativo para restar",
            )
        with c3:
            monto = st.number_input("Monto $ (si fue compra, opcional)", min_value=0.0,
                                    step=1000.0, format="%.0f")
            notas = st.text_area("Notas", height=68)
        submitted = st.form_submit_button("💾 Guardar", type="primary", use_container_width=True)

    if submitted:
        if cantidad == 0:
            st.error("La cantidad no puede ser cero.")
        else:
            db2 = get_session()
            try:
                mov = MovimientoInventario(
                    fecha=fecha,
                    categoria=categoria,
                    cantidad=int(cantidad),
                    tipo_movimiento=tipo_mov,
                    monto=monto if monto > 0 else None,
                    notas=notas.strip() or None,
                )
                db2.add(mov)
                db2.commit()
                st.success(f"✅ Movimiento registrado: {tipo_mov} — {cantidad:+d} {categoria}")
                st.rerun()
            except Exception as e:
                db2.rollback()
                st.error(f"Error: {e}")
            finally:
                db2.close()

# ── Historial de movimientos ──────────────────────────────────────────────────
st.subheader("Historial de movimientos de inventario")
df_movs = load_movimientos_inventario()
if df_movs.empty:
    st.info("Sin movimientos registrados todavía.")
else:
    df_movs["Fecha"] = pd.to_datetime(df_movs["Fecha"])
    editable_table(
        df_movs,
        MovimientoInventario,
        {
            "Fecha": "fecha", "Categoría": "categoria", "Cantidad": "cantidad",
            "Tipo": "tipo_movimiento", "Monto": "monto", "Notas": "notas",
        },
        key="edit_inventario",
        extra_config={
            "Monto": st.column_config.NumberColumn("Monto", format="$ %.0f"),
        },
    )
