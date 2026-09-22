import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_session
from database.models import Venta
from utils.auth import require_auth
from utils.helpers import fmt_pesos, fmt_kgs, load_ventas
from utils.editor import editable_table

st.set_page_config(page_title="Ventas | Campo Ganadero", page_icon="💰", layout="wide")
require_auth()

CATEGORIAS = ["terneros", "terneras", "vacas", "novillos", "toros", "vaquillas", "bueyes", "otro"]

st.title("💰 Ventas y Cargas")
st.markdown("---")

# ── Formulario de carga ───────────────────────────────────────────────────────
with st.expander("➕ Registrar nueva venta", expanded=False):
    with st.form("form_venta", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input("Fecha", value=date.today())
            categoria = st.selectbox("Categoría", CATEGORIAS)
        with c2:
            cantidad = st.number_input("Cantidad (cabezas)", min_value=1, step=1)
            kgs = st.number_input("Kgs totales (opcional)", min_value=0.0, step=1.0,
                                  format="%.0f", value=0.0)
        with c3:
            precio_total = st.number_input("Precio total ($)", min_value=0.0, step=1000.0,
                                           format="%.0f")
            notas = st.text_area("Notas (opcional)", height=68)
        submitted = st.form_submit_button("💾 Guardar venta", type="primary", use_container_width=True)

    if submitted:
        if precio_total <= 0:
            st.error("El precio total debe ser mayor a cero.")
        else:
            db = get_session()
            try:
                venta = Venta(
                    fecha=fecha,
                    categoria=categoria,
                    cantidad=int(cantidad),
                    kgs=kgs if kgs > 0 else None,
                    precio_total=precio_total,
                    notas=notas.strip() or None,
                )
                db.add(venta)
                db.commit()
                st.success(f"✅ Venta registrada: {int(cantidad)} {categoria} — {fmt_pesos(precio_total)}")
                st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"Error al guardar: {e}")
            finally:
                db.close()

# ── Tabla de ventas ───────────────────────────────────────────────────────────
st.subheader("Historial de ventas")

df = load_ventas()

if df.empty:
    st.info("Todavía no hay ventas registradas.")
else:
    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        cats = ["Todas"] + sorted(df["Categoría"].unique().tolist())
        cat_sel = st.selectbox("Filtrar por categoría", cats, key="f_cat_ventas")
    with col_f2:
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        años = ["Todos"] + sorted(df["Fecha"].dt.year.unique().tolist(), reverse=True)
        año_sel = st.selectbox("Filtrar por año", años, key="f_año_ventas")
    with col_f3:
        pass  # espacio para futuros filtros

    filtrado = df.copy()
    if cat_sel != "Todas":
        filtrado = filtrado[filtrado["Categoría"] == cat_sel]
    if año_sel != "Todos":
        filtrado = filtrado[filtrado["Fecha"].dt.year == int(año_sel)]

    # Métricas del filtro
    m1, m2, m3 = st.columns(3)
    m1.metric("Cabezas vendidas", int(filtrado["Cantidad"].sum()))
    m2.metric("Kgs totales", fmt_kgs(filtrado["Kgs"].sum()))
    m3.metric("Total ingresos", fmt_pesos(filtrado["Precio Total"].sum()))

    # Tabla editable (edición directa sobre la grilla)
    editable_table(
        filtrado,
        Venta,
        {
            "Fecha": "fecha", "Categoría": "categoria", "Cantidad": "cantidad",
            "Kgs": "kgs", "Precio Total": "precio_total", "Notas": "notas",
        },
        key="edit_ventas",
        extra_config={
            "Precio Total": st.column_config.NumberColumn("Precio Total", format="$ %.0f"),
            "Kgs": st.column_config.NumberColumn("Kgs", format="%.0f kg"),
        },
    )
