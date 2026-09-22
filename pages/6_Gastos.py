import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database.connection import get_session
from database.models import Gasto
from utils.auth import require_auth
from utils.helpers import fmt_pesos, load_gastos
from utils.editor import editable_table

st.set_page_config(page_title="Gastos | Campo Ganadero", page_icon="💸", layout="wide")
require_auth()

TIPOS_GASTO = [
    "sanidad / veterinario", "medicamentos / vacunas", "suplementos / minerales",
    "forraje / alimentación", "personal / mano de obra", "combustible",
    "maquinaria / reparaciones", "alambrados / infraestructura", "fletes",
    "impuestos / tasas", "semillas / agroquímicos", "otro",
]

st.title("💸 Gastos del Campo")
st.markdown("---")

# ── Formulario ────────────────────────────────────────────────────────────────
with st.expander("➕ Registrar nuevo gasto", expanded=False):
    with st.form("form_gasto", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input("Fecha", value=date.today())
            tipo = st.selectbox("Tipo de gasto", TIPOS_GASTO)
            tipo_custom = st.text_input("Tipo personalizado (si elegiste 'otro')")
        with c2:
            monto = st.number_input("Monto ($)", min_value=0.0, step=100.0, format="%.0f")
            proveedor = st.text_input("Proveedor (opcional)")
        with c3:
            descripcion = st.text_area("Descripción", height=80)
            notas = st.text_input("Notas adicionales (opcional)")
        submitted = st.form_submit_button("💾 Guardar gasto", type="primary", use_container_width=True)

    if submitted:
        if monto <= 0:
            st.error("El monto debe ser mayor a cero.")
        else:
            tipo_final = tipo_custom.strip() if tipo == "otro" and tipo_custom.strip() else tipo
            db = get_session()
            try:
                gasto = Gasto(
                    fecha=fecha,
                    tipo=tipo_final,
                    descripcion=descripcion.strip() or None,
                    monto=monto,
                    proveedor=proveedor.strip() or None,
                    notas=notas.strip() or None,
                )
                db.add(gasto)
                db.commit()
                st.success(f"✅ Gasto registrado: {tipo_final} — {fmt_pesos(monto)}")
                st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"Error: {e}")
            finally:
                db.close()

# ── Tabla y gráficos ──────────────────────────────────────────────────────────
df = load_gastos()

if df.empty:
    st.info("Sin gastos registrados todavía.")
else:
    df["Fecha"] = pd.to_datetime(df["Fecha"])

    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        años = ["Todos"] + sorted(df["Fecha"].dt.year.unique().tolist(), reverse=True)
        año_sel = st.selectbox("Filtrar por año", años, key="f_año_gasto")
    with col_f2:
        tipos = ["Todos"] + sorted(df["Tipo"].unique().tolist())
        tipo_sel = st.selectbox("Filtrar por tipo", tipos, key="f_tipo_gasto")

    filtrado = df.copy()
    if año_sel != "Todos":
        filtrado = filtrado[filtrado["Fecha"].dt.year == int(año_sel)]
    if tipo_sel != "Todos":
        filtrado = filtrado[filtrado["Tipo"] == tipo_sel]

    # KPIs
    st.metric("Total gastos en el filtro", fmt_pesos(filtrado["Monto"].sum()))

    col_tab, col_graf = st.columns([2, 1])
    with col_tab:
        editable_table(
            filtrado,
            Gasto,
            {
                "Fecha": "fecha", "Tipo": "tipo", "Descripción": "descripcion",
                "Monto": "monto", "Proveedor": "proveedor", "Notas": "notas",
            },
            key="edit_gastos",
            extra_config={
                "Monto": st.column_config.NumberColumn("Monto", format="$ %.0f"),
            },
        )

    with col_graf:
        st.markdown("**Por tipo**")
        por_tipo = filtrado.groupby("Tipo")["Monto"].sum().reset_index()
        fig = px.pie(por_tipo, names="Tipo", values="Monto",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Evolución mensual**")
        filtrado["Mes"] = filtrado["Fecha"].dt.to_period("M").astype(str)
        por_mes = filtrado.groupby("Mes")["Monto"].sum().reset_index()
        fig2 = px.bar(por_mes, x="Mes", y="Monto",
                      color_discrete_sequence=["#ef6c00"])
        fig2.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)
