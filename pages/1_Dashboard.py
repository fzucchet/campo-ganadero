import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from utils.auth import require_auth
from utils.helpers import fmt_pesos, fmt_kgs, load_ventas, load_mortandad, load_trabajos, load_gastos

st.set_page_config(page_title="Dashboard | Campo Ganadero", page_icon="📊", layout="wide")
require_auth()

st.title("📊 Dashboard")
st.markdown("Resumen del año en curso")
st.markdown("---")

año_actual = date.today().year

df_ventas = load_ventas()
df_mort = load_mortandad()
df_trab = load_trabajos()
df_gastos = load_gastos()

# Filtrar por año actual
def filtrar_anio(df, col="Fecha"):
    if df.empty or col not in df.columns:
        return df
    df[col] = pd.to_datetime(df[col])
    return df[df[col].dt.year == año_actual]

v = filtrar_anio(df_ventas)
m = filtrar_anio(df_mort)
g = filtrar_anio(df_gastos)

# ── KPIs principales ──────────────────────────────────────────────────────────
st.subheader(f"Indicadores {año_actual}")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    total_ingresos = v["Precio Total"].sum() if not v.empty else 0
    st.metric("💰 Ingresos por ventas", fmt_pesos(total_ingresos))
with c2:
    total_kgs = v["Kgs"].sum() if not v.empty else 0
    st.metric("⚖️ Kgs vendidos", fmt_kgs(total_kgs))
with c3:
    total_cabezas_vendidas = int(v["Cantidad"].sum()) if not v.empty else 0
    st.metric("🐄 Cabezas vendidas", total_cabezas_vendidas)
with c4:
    total_bajas = len(m)
    st.metric("💀 Bajas (mortandad)", total_bajas)
with c5:
    total_gastos = g["Monto"].sum() if not g.empty else 0
    st.metric("💸 Gastos totales", fmt_pesos(total_gastos))

st.markdown("---")

# ── Gráficos ──────────────────────────────────────────────────────────────────
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("Ingresos por ventas (mensual)")
    if not v.empty:
        v["Mes"] = v["Fecha"].dt.to_period("M").astype(str)
        ventas_mes = v.groupby("Mes")["Precio Total"].sum().reset_index()
        ventas_mes.columns = ["Mes", "Ingresos"]
        fig = px.bar(ventas_mes, x="Mes", y="Ingresos",
                     color_discrete_sequence=["#2e7d32"],
                     labels={"Ingresos": "$", "Mes": "Mes"})
        fig.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos de ventas para el año actual.")

with col_der:
    st.subheader("Mortandad por categoría")
    if not m.empty:
        mort_cat = m["Categoría"].value_counts().reset_index()
        mort_cat.columns = ["Categoría", "Cantidad"]
        fig2 = px.pie(mort_cat, names="Categoría", values="Cantidad",
                      color_discrete_sequence=px.colors.qualitative.Set2)
        fig2.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sin registros de mortandad para el año actual.")

col_izq2, col_der2 = st.columns(2)

with col_izq2:
    st.subheader("Gastos por tipo")
    if not g.empty:
        gastos_tipo = g.groupby("Tipo")["Monto"].sum().reset_index()
        fig3 = px.pie(gastos_tipo, names="Tipo", values="Monto",
                      color_discrete_sequence=px.colors.qualitative.Pastel)
        fig3.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Sin gastos registrados para el año actual.")

with col_der2:
    st.subheader("Kgs vendidos por categoría")
    if not v.empty and v["Kgs"].notna().any():
        kgs_cat = v.groupby("Categoría")["Kgs"].sum().reset_index()
        kgs_cat = kgs_cat[kgs_cat["Kgs"] > 0]
        fig4 = px.bar(kgs_cat, x="Categoría", y="Kgs",
                      color="Categoría",
                      labels={"Kgs": "Kg totales"},
                      color_discrete_sequence=px.colors.qualitative.Safe)
        fig4.update_layout(margin=dict(t=10, b=10), showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Sin datos de kgs por categoría.")

st.markdown("---")

# ── Últimos trabajos ──────────────────────────────────────────────────────────
st.subheader("Últimos trabajos a corral")
if not df_trab.empty:
    st.dataframe(df_trab.head(10).drop(columns=["ID"]), use_container_width=True, hide_index=True)
else:
    st.info("Sin trabajos registrados aún.")
