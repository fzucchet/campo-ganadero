import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_session
from database.models import TrabajoCorral, TipoTrabajoCatalogo
from utils.auth import require_auth
from utils.helpers import (
    load_trabajos, load_catalogo_tipos, get_tipos_por_categoria,
    categoria_de_tipos, seed_catalogo_tipos_si_vacio,
    CATEGORIAS_TRABAJO_ORDEN, CATEGORIAS_TRABAJO_EMOJI,
)
from utils.editor import editable_table

st.set_page_config(page_title="Trabajos a Corral | Campo Ganadero", page_icon="🔧", layout="wide")
require_auth()

# Cargar el catálogo inicial si todavía está vacío
seed_catalogo_tipos_si_vacio()

st.title("🔧 Trabajos a Corral")
st.markdown("Sanidad, pesajes, vacunaciones y manejo")
st.markdown("---")

# ── Menú: administrar tipos de trabajo (catálogo dinámico) ────────────────────
with st.expander("⚙️ Administrar tipos de trabajo", expanded=False):
    st.caption("Definí acá los tipos disponibles. Después los combinás con checks al registrar un trabajo.")

    with st.form("form_nuevo_tipo", clear_on_submit=True):
        cc1, cc2, cc3 = st.columns([2, 2, 1])
        with cc1:
            nuevo_nombre = st.text_input("Nuevo tipo", placeholder="Ej: desparasitación")
        with cc2:
            nueva_cat = st.selectbox("Categoría", CATEGORIAS_TRABAJO_ORDEN,
                                     format_func=lambda c: CATEGORIAS_TRABAJO_EMOJI.get(c, c))
        with cc3:
            st.markdown("<br>", unsafe_allow_html=True)
            add_tipo = st.form_submit_button("➕ Agregar", use_container_width=True)

    if add_tipo:
        nombre_limpio = nuevo_nombre.strip()
        if not nombre_limpio:
            st.warning("Escribí un nombre para el tipo.")
        else:
            db = get_session()
            try:
                existe = db.query(TipoTrabajoCatalogo).filter(
                    TipoTrabajoCatalogo.nombre == nombre_limpio
                ).first()
                if existe:
                    st.warning(f"El tipo «{nombre_limpio}» ya existe.")
                else:
                    db.add(TipoTrabajoCatalogo(nombre=nombre_limpio, categoria=nueva_cat, activo=True))
                    db.commit()
                    st.success(f"✅ Tipo agregado: {nombre_limpio}")
                    st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"Error al agregar: {e}")
            finally:
                db.close()

    cat_df = load_catalogo_tipos()
    if cat_df.empty:
        st.info("Sin tipos en el catálogo.")
    else:
        st.markdown("**Tipos existentes** — editá el nombre, la categoría o el estado activo:")
        editable_table(
            cat_df,
            TipoTrabajoCatalogo,
            {"Nombre": "nombre", "Categoría": "categoria", "Activo": "activo"},
            key="edit_catalogo_tipos",
            extra_config={
                "Categoría": st.column_config.SelectboxColumn(
                    "Categoría", options=CATEGORIAS_TRABAJO_ORDEN,
                ),
                "Activo": st.column_config.CheckboxColumn(
                    "Activo", help="Destildá para ocultarlo del alta sin borrarlo.",
                ),
            },
            caption="✏️ Editá en la grilla. Marcá 🗑️ para borrar tipos. Presioná Guardar.",
        )

# ── Formulario: registrar nuevo trabajo (combinando tipos con checks) ─────────
tipos_por_cat = get_tipos_por_categoria(solo_activos=True)

with st.expander("➕ Registrar nuevo trabajo", expanded=False):
    with st.form("form_trabajo", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            fecha = st.date_input("Fecha", value=date.today())
        with c2:
            animales = st.text_area("Animales trabajados", height=80,
                                    placeholder="Ej: 205 terneras + 36 vaquillas en espera")

        st.markdown("**Tipos de trabajo realizados** (marcá todos los que apliquen)")
        seleccionados = []
        for categoria in tipos_por_cat:
            st.markdown(f"_{CATEGORIAS_TRABAJO_EMOJI.get(categoria, categoria)}_")
            nombres = tipos_por_cat[categoria]
            cols = st.columns(3)
            for idx, nombre in enumerate(nombres):
                with cols[idx % 3]:
                    if st.checkbox(nombre, key=f"chk_{categoria}_{nombre}"):
                        seleccionados.append(nombre)

        tipo_custom = st.text_input("Otro tipo no listado (opcional)",
                                    placeholder="Ej: curación de miasis")
        resultado = st.text_area("Resultado / observaciones", height=80,
                                 placeholder="Ej: 322 vacas preñadas, 110 vacías")
        notas = st.text_input("Notas adicionales (opcional)")
        submitted = st.form_submit_button("💾 Guardar trabajo", type="primary", use_container_width=True)

    if submitted:
        tipos_finales = list(seleccionados)
        if tipo_custom.strip():
            tipos_finales.append(tipo_custom.strip())

        if not tipos_finales:
            st.warning("Marcá al menos un tipo de trabajo (o escribí uno en 'Otro tipo').")
        else:
            tipo_texto = " + ".join(tipos_finales)
            categoria_final = categoria_de_tipos(seleccionados) if seleccionados else "Otro"
            db = get_session()
            try:
                trabajo = TrabajoCorral(
                    fecha=fecha,
                    categoria=categoria_final,
                    tipo_trabajo=tipo_texto,
                    animales=animales.strip() or None,
                    resultado=resultado.strip() or None,
                    notas=notas.strip() or None,
                )
                db.add(trabajo)
                db.commit()
                st.success(f"✅ Trabajo registrado: {tipo_texto} — {fecha.strftime('%d/%m/%Y')}")
                st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"Error al guardar: {e}")
            finally:
                db.close()

# ── Tabla ─────────────────────────────────────────────────────────────────────
df = load_trabajos()

if df.empty:
    st.info("Sin trabajos registrados todavía.")
else:
    df["Fecha"] = pd.to_datetime(df["Fecha"])

    # Filtros
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        cats = ["Todas"] + sorted(df["Categoría"].unique().tolist())
        cat_sel = st.selectbox("Filtrar por categoría", cats, key="f_cat_trab")
    with col_f2:
        tipos = ["Todos"] + sorted(df["Tipo de Trabajo"].unique().tolist())
        tipo_sel = st.selectbox("Filtrar por tipo", tipos, key="f_tipo_trab")
    with col_f3:
        años = ["Todos"] + sorted(df["Fecha"].dt.year.unique().tolist(), reverse=True)
        año_sel = st.selectbox("Filtrar por año", años, key="f_año_trab")
    with col_f4:
        meses_dict = {
            "Todos": 0, "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
            "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
            "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
        }
        mes_sel = st.selectbox("Filtrar por mes", list(meses_dict.keys()), key="f_mes_trab")

    filtrado = df.copy()
    if cat_sel != "Todas":
        filtrado = filtrado[filtrado["Categoría"] == cat_sel]
    if tipo_sel != "Todos":
        filtrado = filtrado[filtrado["Tipo de Trabajo"] == tipo_sel]
    if año_sel != "Todos":
        filtrado = filtrado[filtrado["Fecha"].dt.year == int(año_sel)]
    if mes_sel != "Todos":
        filtrado = filtrado[filtrado["Fecha"].dt.month == meses_dict[mes_sel]]

    st.markdown(f"**{len(filtrado)} registros encontrados**")

    editable_table(
        filtrado,
        TrabajoCorral,
        {
            "Fecha": "fecha", "Categoría": "categoria", "Tipo de Trabajo": "tipo_trabajo",
            "Animales": "animales", "Resultado": "resultado", "Notas": "notas",
        },
        key="edit_trabajos",
        extra_config={
            "Categoría": st.column_config.SelectboxColumn(
                "Categoría", options=[*CATEGORIAS_TRABAJO_ORDEN, "Mixto"],
            ),
        },
    )
