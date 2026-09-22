import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database.connection import get_session
from database.models import Mortandad
from utils.auth import require_auth
from utils.helpers import load_mortandad
from utils.editor import editable_table

st.set_page_config(page_title="Mortandad | Campo Ganadero", page_icon="💀", layout="wide")
require_auth()

CATEGORIAS = ["ternero", "ternera", "vaca", "toro", "novillo", "vaquilla", "buey", "otro"]

st.title("💀 Mortandad")
st.markdown("Registro de bajas de hacienda")
st.markdown("---")

# ── Formulario de carga ───────────────────────────────────────────────────────
with st.expander("➕ Registrar nueva baja", expanded=False):
    with st.form("form_mort", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input("Fecha", value=date.today())
            categoria = st.selectbox("Categoría", CATEGORIAS)
        with c2:
            numero_caravana = st.number_input("Nro. caravana (opcional)", min_value=0, step=1, value=0)
            potrero = st.text_input("Potrero (opcional)")
        with c3:
            descripcion = st.text_area("Descripción / causa", height=100)
        submitted = st.form_submit_button("💾 Guardar baja", type="primary", use_container_width=True)

    if submitted:
        db = get_session()
        try:
            baja = Mortandad(
                fecha=fecha,
                categoria=categoria,
                descripcion=descripcion.strip() or None,
                numero_caravana=int(numero_caravana) if numero_caravana > 0 else None,
                potrero=potrero.strip() or None,
            )
            db.add(baja)
            db.commit()
            st.success(f"✅ Baja registrada: {categoria} — {fecha.strftime('%d/%m/%Y')}")
            st.rerun()
        except Exception as e:
            db.rollback()
            st.error(f"Error al guardar: {e}")
        finally:
            db.close()

# ── Tabla y métricas ──────────────────────────────────────────────────────────
df = load_mortandad()

if df.empty:
    st.info("Sin registros de mortandad todavía.")
else:
    df["Fecha"] = pd.to_datetime(df["Fecha"])

    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        cats = ["Todas"] + sorted(df["Categoría"].unique().tolist())
        cat_sel = st.selectbox("Filtrar por categoría", cats, key="f_cat_mort")
    with col_f2:
        años = ["Todos"] + sorted(df["Fecha"].dt.year.unique().tolist(), reverse=True)
        año_sel = st.selectbox("Filtrar por año", años, key="f_año_mort")

    filtrado = df.copy()
    if cat_sel != "Todas":
        filtrado = filtrado[filtrado["Categoría"] == cat_sel]
    if año_sel != "Todos":
        filtrado = filtrado[filtrado["Fecha"].dt.year == int(año_sel)]

    st.metric("Total bajas en el filtro", len(filtrado))

    # Gráfico
    col_tab, col_graf = st.columns([2, 1])
    with col_tab:
        editable_table(
            filtrado,
            Mortandad,
            {
                "Fecha": "fecha", "Categoría": "categoria", "Descripción": "descripcion",
                "Nro Caravana": "numero_caravana", "Potrero": "potrero",
            },
            key="edit_mortandad",
        )

    with col_graf:
        st.markdown("**Por categoría**")
        por_cat = filtrado["Categoría"].value_counts().reset_index()
        por_cat.columns = ["Categoría", "Cantidad"]
        fig = px.pie(por_cat, names="Categoría", values="Cantidad",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(margin=dict(t=10, b=10), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Por mes**")
        filtrado["Mes"] = filtrado["Fecha"].dt.to_period("M").astype(str)
        por_mes = filtrado["Mes"].value_counts().sort_index().reset_index()
        por_mes.columns = ["Mes", "Cantidad"]
        fig2 = px.bar(por_mes, x="Mes", y="Cantidad",
                      color_discrete_sequence=["#c62828"])
        fig2.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)
