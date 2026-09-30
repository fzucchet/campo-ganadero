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

# ── Formulario de lote mixto ──────────────────────────────────────────────────
with st.expander("➕➕ Registrar lote mixto (varias categorías, un solo pesaje/precio)", expanded=False):
    st.caption(
        "Cargá las categorías y cantidades del lote. Se pesa todo junto y el precio por kilo es el "
        "mismo, así que el total (kgs y precio) queda en la primera categoría; las demás sólo "
        "aportan su cantidad para descontar del stock."
    )
    with st.form("form_lote", clear_on_submit=True):
        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            fecha_lote = st.date_input("Fecha", value=date.today(), key="lote_fecha")
        with lc2:
            kgs_lote = st.number_input("Kgs totales del lote", min_value=0.0, step=1.0,
                                       format="%.0f", value=0.0, key="lote_kgs")
        with lc3:
            precio_lote = st.number_input("Precio total del lote ($)", min_value=0.0, step=1000.0,
                                          format="%.0f", key="lote_precio")

        composicion = st.data_editor(
            pd.DataFrame({"Categoría": ["terneros", "terneras"], "Cantidad": [0, 0]}),
            column_config={
                "Categoría": st.column_config.SelectboxColumn("Categoría", options=CATEGORIAS, required=True),
                "Cantidad": st.column_config.NumberColumn("Cantidad (cabezas)", min_value=0, step=1),
            },
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            key="lote_comp",
        )
        notas_lote = st.text_input("Notas (opcional)", key="lote_notas")
        submit_lote = st.form_submit_button("💾 Guardar lote mixto", type="primary", use_container_width=True)

    if submit_lote:
        lineas: dict[str, int] = {}
        for _, r in composicion.iterrows():
            cat = str(r["Categoría"]).strip().lower() if r["Categoría"] else ""
            cant = int(r["Cantidad"] or 0)
            if cat and cant > 0:
                lineas[cat] = lineas.get(cat, 0) + cant
        total_cab = sum(lineas.values())

        if not lineas:
            st.error("Cargá al menos una categoría con cantidad mayor a cero.")
        elif precio_lote <= 0:
            st.error("El precio total del lote debe ser mayor a cero.")
        else:
            comp_txt = " + ".join(f"{c} {cat}" for cat, c in lineas.items())
            composicion = ",".join(f"{cat}:{c}" for cat, c in lineas.items())
            nota_base = (notas_lote.strip() + " · " if notas_lote.strip() else "")
            es_mixto = len(lineas) > 1
            db = get_session()
            try:
                if es_mixto:
                    db.add(Venta(
                        fecha=fecha_lote, categoria="mixto", cantidad=total_cab,
                        kgs=kgs_lote if kgs_lote > 0 else None,
                        precio_total=precio_lote, composicion=composicion,
                        notas=f"{nota_base}Lote mixto: {comp_txt} (pesados juntos, precio único)",
                    ))
                else:
                    cat, cant = next(iter(lineas.items()))
                    db.add(Venta(
                        fecha=fecha_lote, categoria=cat, cantidad=cant,
                        kgs=kgs_lote if kgs_lote > 0 else None,
                        precio_total=precio_lote,
                        notas=nota_base.rstrip(" · ") or None,
                    ))
                db.commit()
                st.success(f"✅ Venta registrada: {comp_txt} — {fmt_pesos(precio_lote)}")
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
            "Kgs": "kgs", "Precio Total": "precio_total",
            "Composición": "composicion", "Notas": "notas",
        },
        key="edit_ventas",
        extra_config={
            "Precio Total": st.column_config.NumberColumn("Precio Total", format="$ %.0f"),
            "Kgs": st.column_config.NumberColumn("Kgs", format="%.0f kg"),
            "Composición": st.column_config.TextColumn("Composición", help="Lote mixto: cabezas por categoría que descuentan stock."),
        },
    )
