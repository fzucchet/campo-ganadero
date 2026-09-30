import streamlit as st
from datetime import date
from database.connection import get_session
from database.models import Venta, Mortandad, TrabajoCorral, MovimientoInventario
from utils.auth import require_auth
from utils.parser_carga import parse_texto
from utils.helpers import CATEGORIAS_TRABAJO_ORDEN

st.set_page_config(page_title="Carga Rápida | Campo Ganadero", page_icon="⚡", layout="wide")
require_auth()

CAT_VENTA = ["terneros", "terneras", "vacas", "novillos", "toros", "vaquillas", "bueyes", "mixto", "otro"]
CAT_MORT = ["ternero", "ternera", "vaca", "toro", "novillo", "vaquilla", "buey", "otro"]
CAT_INV = ["terneros", "terneras", "vacas", "novillos", "toros", "vaquillas", "bueyes"]
TIPOS_MOV = ["compra", "nacimiento", "destete", "ajuste de inventario", "otro ingreso"]
TIPOS_REGISTRO = ["mortandad", "venta", "inventario", "trabajo"]
TIPO_LABEL = {
    "mortandad": "💀 Mortandad",
    "venta": "💰 Venta / Carga",
    "inventario": "📦 Movimiento de inventario",
    "trabajo": "🔧 Trabajo a corral",
}

st.title("⚡ Carga Rápida")
st.markdown("Escribí en lenguaje natural y el sistema lo interpreta. **Nada se guarda sin tu confirmación.**")
st.markdown("---")

with st.expander("💡 Ejemplos de frases que entiende"):
    st.markdown("""
- *se encontró un ternero muerto en el potrero 63*
- *se cargaron 100 terneros machos, 20.000 kgs a 1500 el kilo*
- *vendí 30 vacas por 45.000.000*
- *compré 50 terneras por 30.000.000*
- *vacuné 200 terneras con aftosa*
- *100 vacas con ivermectina y suplenut y 50 terneros con ricobendazol* → genera **dos** registros
    """)

texto = st.text_area(
    "Describí el movimiento",
    placeholder="Ej: se cargaron 100 terneros machos, 20.000 kgs a 1500 el kilo",
    height=90,
    key="texto_carga",
)

if st.button("🔍 Interpretar", type="primary"):
    resultados = parse_texto(texto)
    if not resultados:
        st.session_state.pop("parse_results", None)
        st.warning(
            "No pude interpretar el texto. Probá ser más explícito "
            "(ej: incluí una categoría como *terneros*, *vacas*, y qué pasó: *muerto*, *vendí*, *compré*, *vacuné*)."
        )
    else:
        st.session_state.parse_results = resultados


CONF_EMOJI = {"alta": "🟢", "media": "🟡", "baja": "🔴"}


def _campos_registro(tipo: str, campos: dict, idx: int) -> dict:
    """Renderiza los campos editables de un registro y devuelve los valores actuales."""
    vals: dict = {}
    if tipo == "mortandad":
        c1, c2, c3 = st.columns(3)
        with c1:
            vals["fecha"] = st.date_input("Fecha", value=campos.get("fecha", date.today()), key=f"f_{idx}")
        with c2:
            cv = campos.get("categoria", "otro")
            vals["categoria"] = st.selectbox("Categoría", CAT_MORT,
                                             index=CAT_MORT.index(cv) if cv in CAT_MORT else len(CAT_MORT) - 1,
                                             key=f"cat_{idx}")
        with c3:
            vals["potrero"] = st.text_input("Potrero", value=campos.get("potrero", ""), key=f"pot_{idx}")
        vals["descripcion"] = st.text_area("Descripción / causa", value=campos.get("descripcion", ""), key=f"desc_{idx}")

    elif tipo == "venta":
        comp = campos.get("composicion")
        if comp:
            legible = " + ".join(f"{p.split(':')[1]} {p.split(':')[0]}" for p in comp.split(",") if ":" in p)
            st.caption(f"🔗 Lote mixto (una sola venta) — descuenta del stock: **{legible}**")
        vals["composicion"] = comp
        c1, c2, c3 = st.columns(3)
        with c1:
            vals["fecha"] = st.date_input("Fecha", value=campos.get("fecha", date.today()), key=f"f_{idx}")
            cv = campos.get("categoria", "terneros")
            vals["categoria"] = st.selectbox("Categoría", CAT_VENTA,
                                             index=CAT_VENTA.index(cv) if cv in CAT_VENTA else 0, key=f"cat_{idx}")
        with c2:
            vals["cantidad"] = st.number_input("Cantidad (cabezas)", min_value=0, step=1,
                                               value=int(campos.get("cantidad") or 0), key=f"cant_{idx}")
            vals["kgs"] = st.number_input("Kgs totales", min_value=0.0, step=1.0, format="%.0f",
                                          value=float(campos.get("kgs") or 0.0), key=f"kgs_{idx}")
        with c3:
            vals["precio_total"] = st.number_input("Precio total ($)", min_value=0.0, step=1000.0, format="%.0f",
                                                   value=float(campos.get("precio_total") or 0.0), key=f"pre_{idx}")
            vals["notas"] = st.text_area("Notas", value=campos.get("notas", ""), height=68, key=f"not_{idx}")

    elif tipo == "inventario":
        c1, c2, c3 = st.columns(3)
        with c1:
            vals["fecha"] = st.date_input("Fecha", value=campos.get("fecha", date.today()), key=f"f_{idx}")
            cv = campos.get("categoria", "terneros")
            vals["categoria"] = st.selectbox("Categoría", CAT_INV,
                                             index=CAT_INV.index(cv) if cv in CAT_INV else 0, key=f"cat_{idx}")
        with c2:
            vals["cantidad"] = st.number_input("Cantidad (cabezas)", min_value=0, step=1,
                                               value=int(campos.get("cantidad") or 0), key=f"cant_{idx}")
            mv = campos.get("tipo_movimiento", "compra")
            vals["tipo_movimiento"] = st.selectbox("Tipo de movimiento", TIPOS_MOV,
                                                   index=TIPOS_MOV.index(mv) if mv in TIPOS_MOV else 0, key=f"tm_{idx}")
        with c3:
            vals["monto"] = st.number_input("Monto ($, opcional)", min_value=0.0, step=1000.0, format="%.0f",
                                            value=float(campos.get("monto") or 0.0), key=f"mon_{idx}")
            vals["notas"] = st.text_area("Notas", value=campos.get("notas", ""), height=68, key=f"not_{idx}")

    else:  # trabajo
        c1, c2 = st.columns(2)
        with c1:
            vals["fecha"] = st.date_input("Fecha", value=campos.get("fecha", date.today()), key=f"f_{idx}")
            cv = campos.get("categoria", "Sanidad")
            vals["categoria"] = st.selectbox("Categoría", CATEGORIAS_TRABAJO_ORDEN,
                                             index=CATEGORIAS_TRABAJO_ORDEN.index(cv)
                                             if cv in CATEGORIAS_TRABAJO_ORDEN else 0, key=f"cat_{idx}")
        with c2:
            vals["tipo_trabajo"] = st.text_input("Tipo de trabajo", value=campos.get("tipo_trabajo", ""), key=f"tt_{idx}")
        vals["animales"] = st.text_area("Animales / detalle", value=campos.get("animales", ""), key=f"ani_{idx}")
        vals["resultado"] = st.text_area("Resultado (opcional)", value=campos.get("resultado", ""), key=f"res_{idx}")
    return vals

# ── Vista previa editable (uno o varios registros) ────────────────────────────
if "parse_results" in st.session_state:
    records = st.session_state.parse_results
    st.markdown(f"### 📋 Vista previa — {len(records)} registro(s)")

    # Selector de tipo por registro (fuera del form para que los campos se actualicen).
    tipos = []
    for idx, res in enumerate(records):
        conf = res.get("confianza", "media")
        st.caption(f"**Registro {idx + 1}** — {CONF_EMOJI.get(conf, '🟡')} {conf} · {res.get('resumen', '')}")
        t = st.selectbox(
            f"Tipo de registro {idx + 1}",
            TIPOS_REGISTRO,
            index=TIPOS_REGISTRO.index(res["tipo"]),
            format_func=lambda x: TIPO_LABEL[x],
            key=f"tipo_{idx}",
            label_visibility="collapsed",
        )
        tipos.append(t)

    with st.form("form_confirmar"):
        filas = []
        for idx, res in enumerate(records):
            tipo = tipos[idx]
            st.markdown(f"**Registro {idx + 1} · {TIPO_LABEL[tipo]}**")
            vals = _campos_registro(tipo, res["campos"], idx)
            vals["_tipo"] = tipo
            filas.append(vals)
            if idx < len(records) - 1:
                st.markdown("---")
        guardar = st.form_submit_button("💾 Confirmar y guardar todo", type="primary", use_container_width=True)

    if guardar:
        db = get_session()
        guardados = 0
        # En un lote mixto las categorías secundarias van con precio 0 (sólo descuentan
        # stock); por eso se valida el total de las ventas, no cada fila.
        total_ventas = sum(v["precio_total"] for v in filas if v["_tipo"] == "venta")
        hay_venta = any(v["_tipo"] == "venta" for v in filas)
        if hay_venta and total_ventas <= 0:
            st.error("El precio total de la(s) venta(s) debe ser mayor a cero.")
        else:
            try:
                for v in filas:
                    tipo = v["_tipo"]
                    if tipo == "mortandad":
                        db.add(Mortandad(
                            fecha=v["fecha"], categoria=v["categoria"],
                            descripcion=v["descripcion"].strip() or None,
                            potrero=v["potrero"].strip() or None,
                        ))
                    elif tipo == "venta":
                        db.add(Venta(
                            fecha=v["fecha"], categoria=v["categoria"], cantidad=int(v["cantidad"]),
                            kgs=v["kgs"] if v["kgs"] > 0 else None,
                            precio_total=v["precio_total"], composicion=v.get("composicion") or None,
                            notas=v["notas"].strip() or None,
                        ))
                    elif tipo == "inventario":
                        db.add(MovimientoInventario(
                            fecha=v["fecha"], categoria=v["categoria"], cantidad=int(v["cantidad"]),
                            tipo_movimiento=v["tipo_movimiento"],
                            monto=v["monto"] if v["monto"] > 0 else None,
                            notas=v["notas"].strip() or None,
                        ))
                    else:  # trabajo
                        db.add(TrabajoCorral(
                            fecha=v["fecha"], categoria=v["categoria"],
                            tipo_trabajo=v["tipo_trabajo"].strip() or "sin especificar",
                            animales=v["animales"].strip() or None,
                            resultado=v["resultado"].strip() or None,
                        ))
                    guardados += 1
                db.commit()
                st.session_state.pop("parse_results", None)
                st.success(f"✅ {guardados} registro(s) guardado(s).")
            except Exception as e:
                db.rollback()
                st.error(f"Error al guardar: {e}")
            finally:
                db.close()
