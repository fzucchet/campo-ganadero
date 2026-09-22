import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_session
from database.models import Reproduccion, IndiceReproductivo
from utils.auth import require_auth
from utils.helpers import load_reproduccion, load_indices_reproductivos
from utils.editor import editable_table

st.set_page_config(page_title="Reproducción | Campo Ganadero", page_icon="🐾", layout="wide")
require_auth()

TIPOS = [
    "tacto / diagnóstico de preñez",
    "parto",
    "destete",
    "entrada de toros",
    "salida de toros",
    "sincronización",
    "inseminación artificial",
    "otro",
]

st.title("🐾 Reproducción")
st.markdown("Tactos, partos, destetes y manejo reproductivo")
st.markdown("---")

# ── Formulario ────────────────────────────────────────────────────────────────
with st.expander("➕ Registrar evento reproductivo", expanded=False):
    with st.form("form_repro", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input("Fecha", value=date.today())
            tipo = st.selectbox("Tipo de evento", TIPOS)
        with c2:
            total_animales = st.number_input("Total animales trabajados", min_value=0, step=1)
            prenadas = st.number_input("Preñadas", min_value=0, step=1)
            vacias = st.number_input("Vacías / rechazo", min_value=0, step=1)
        with c3:
            terneros_machos = st.number_input("Terneros machos nacidos/destete", min_value=0, step=1)
            terneras_hembras = st.number_input("Terneras hembras nacidas/destete", min_value=0, step=1)
            notas = st.text_area("Notas", height=68)
        submitted = st.form_submit_button("💾 Guardar evento", type="primary", use_container_width=True)

    if submitted:
        db = get_session()
        try:
            reg = Reproduccion(
                fecha=fecha,
                tipo=tipo,
                total_animales=int(total_animales) if total_animales else None,
                prenadas=int(prenadas) if prenadas else None,
                vacias=int(vacias) if vacias else None,
                terneros_machos=int(terneros_machos) if terneros_machos else None,
                terneras_hembras=int(terneras_hembras) if terneras_hembras else None,
                notas=notas.strip() or None,
            )
            db.add(reg)
            db.commit()
            st.success(f"✅ Evento registrado: {tipo} — {fecha.strftime('%d/%m/%Y')}")
            st.rerun()
        except Exception as e:
            db.rollback()
            st.error(f"Error: {e}")
        finally:
            db.close()

# ── Tabla ─────────────────────────────────────────────────────────────────────
df = load_reproduccion()

if df.empty:
    st.info("Sin registros reproductivos todavía.")
else:
    df["Fecha"] = pd.to_datetime(df["Fecha"])

    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        tipos = ["Todos"] + sorted(df["Tipo"].unique().tolist())
        tipo_sel = st.selectbox("Filtrar por tipo", tipos, key="f_tipo_repro")
    with col_f2:
        años = ["Todos"] + sorted(df["Fecha"].dt.year.unique().tolist(), reverse=True)
        año_sel = st.selectbox("Filtrar por año", años, key="f_año_repro")

    filtrado = df.copy()
    if tipo_sel != "Todos":
        filtrado = filtrado[filtrado["Tipo"] == tipo_sel]
    if año_sel != "Todos":
        filtrado = filtrado[filtrado["Fecha"].dt.year == int(año_sel)]

    # Resumen de tactos
    tactos = filtrado[filtrado["Tipo"].str.contains("tacto", case=False, na=False)]
    if not tactos.empty:
        total_prenadas = tactos["Preñadas"].sum()
        total_vacias = tactos["Vacías"].sum()
        total_tac = tactos["Total Animales"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total tacteadas", int(total_tac) if total_tac else "-")
        c2.metric("Preñadas", int(total_prenadas) if total_prenadas else "-")
        c3.metric("Vacías", int(total_vacias) if total_vacias else "-")

    editable_table(
        filtrado,
        Reproduccion,
        {
            "Fecha": "fecha", "Tipo": "tipo", "Total Animales": "total_animales",
            "Preñadas": "prenadas", "Vacías": "vacias",
            "Terneros M": "terneros_machos", "Terneras H": "terneras_hembras",
            "Notas": "notas",
        },
        key="edit_reproduccion",
    )


# ══════════════════════════════════════════════════════════════════════════════
# ÍNDICES REPRODUCTIVOS POR TEMPORADA (histórico de KPIs)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.header("📈 Índices reproductivos por temporada")
st.caption("Histórico de % preñez y % destete por temporada de servicio. Los porcentajes se calculan automáticamente.")

TEMPORADAS = ["Primavera", "Otoño"]

with st.expander("➕ Cargar índice de una temporada", expanded=False):
    with st.form("form_indice", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            i_temporada = st.selectbox("Temporada", TEMPORADAS)
            i_anio = st.number_input("Año", min_value=1990, max_value=2100, value=date.today().year, step=1)
        with c2:
            i_total = st.number_input("Total tactadas / en servicio", min_value=0, step=1)
            i_prenadas = st.number_input("Preñadas", min_value=0, step=1)
        with c3:
            i_destete = st.number_input("Destetados (opcional)", min_value=0, step=1)
            i_muertos = st.number_input("Muertos parto-destete (opcional)", min_value=0, step=1)
        i_notas = st.text_area("Notas", height=68)
        i_submitted = st.form_submit_button("💾 Guardar índice", type="primary", use_container_width=True)

    if i_submitted:
        if i_total <= 0 or i_prenadas <= 0:
            st.error("Total y Preñadas deben ser mayores a cero.")
        elif i_prenadas > i_total:
            st.error("Las preñadas no pueden superar el total.")
        else:
            db = get_session()
            try:
                existe = db.query(IndiceReproductivo).filter(
                    IndiceReproductivo.temporada == i_temporada,
                    IndiceReproductivo.anio == int(i_anio),
                ).first()
                if existe:
                    st.error(f"Ya existe un registro para {i_temporada} {int(i_anio)}. Eliminalo primero si querés reemplazarlo.")
                else:
                    reg = IndiceReproductivo(
                        temporada=i_temporada,
                        anio=int(i_anio),
                        total=int(i_total),
                        prenadas=int(i_prenadas),
                        destete=int(i_destete) if i_destete else None,
                        muertos_parto_destete=int(i_muertos) if i_muertos else None,
                        notas=i_notas.strip() or None,
                    )
                    db.add(reg)
                    db.commit()
                    st.success(f"✅ Índice guardado: {i_temporada} {int(i_anio)}")
                    st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"Error: {e}")
            finally:
                db.close()

df_ind = load_indices_reproductivos()

if df_ind.empty:
    st.info("Sin índices reproductivos cargados. Ejecutá `python3 seed_indices_reproductivos.py` para cargar el histórico, o usá el formulario de arriba.")
else:
    # Métricas del promedio histórico
    prom_prenez = df_ind["% Preñez"].mean()
    con_destete = df_ind[df_ind["% Destete"].notna()]
    prom_destete = con_destete["% Destete"].mean() if not con_destete.empty else None
    mejor = df_ind.loc[df_ind["% Preñez"].idxmax()]

    m1, m2, m3 = st.columns(3)
    m1.metric("% Preñez promedio", f"{prom_prenez:.1f}%")
    m2.metric("% Destete promedio", f"{prom_destete:.1f}%" if prom_destete is not None else "-")
    m3.metric("Mejor temporada", f"{mejor['Etiqueta']}", f"{mejor['% Preñez']:.1f}% preñez")

    # Gráfico de tendencias
    chart_df = df_ind.set_index("Etiqueta")[["% Preñez", "% Destete"]]
    st.line_chart(chart_df, height=320)

    # Tabla editable (los % se recalculan al guardar)
    st.caption("Editá los valores crudos; los % se recalculan solos al guardar.")
    editable_table(
        df_ind.iloc[::-1].drop(columns=["Etiqueta"]),
        IndiceReproductivo,
        {
            "Temporada": "temporada", "Año": "anio", "Total": "total",
            "Preñadas": "prenadas", "Destete": "destete",
            "Muertos Parto-Destete": "muertos_parto_destete", "Notas": "notas",
        },
        key="edit_indices",
        disabled=["% Preñez", "% Destete"],
        extra_config={
            "% Preñez": st.column_config.NumberColumn("% Preñez", format="%.1f%%", disabled=True),
            "% Destete": st.column_config.NumberColumn("% Destete", format="%.1f%%", disabled=True),
        },
        caption=None,
    )
