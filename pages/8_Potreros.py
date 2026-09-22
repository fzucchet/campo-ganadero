import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_session
from database.models import Potrero, AsignacionPotrero
from utils.auth import require_auth
from utils.helpers import (
    load_potreros, load_asignaciones, load_trabajos,
    stock_por_potrero, load_movimientos_potrero, registrar_movimiento_potrero,
)
from utils.editor import editable_table

st.set_page_config(page_title="Potreros | Campo Ganadero", page_icon="🌿", layout="wide")
require_auth()

CATEGORIAS = ["terneros", "terneras", "vacas", "novillos", "toros", "vaquillas", "bueyes", "mixto"]

st.title("🌿 Potreros")
st.markdown("Gestión de potreros y asignación de hacienda")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🗺️ Potreros", "🐄 Asignaciones", "🔁 Movimientos"])

# ── TAB 1: Gestión de potreros ────────────────────────────────────────────────
with tab1:
    with st.expander("➕ Agregar nuevo potrero", expanded=False):
        with st.form("form_potrero", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                nombre = st.text_input("Nombre del potrero", placeholder="Ej: Tacuruzal, Potrero del Corral")
            with c2:
                numero = st.text_input("Número / código (opcional)", placeholder="Ej: 62, 63")
                hectareas = st.number_input("Hectáreas (opcional)", min_value=0.0, step=0.5, format="%.1f")
            with c3:
                notas = st.text_area("Notas", height=80)
            submitted = st.form_submit_button("💾 Guardar potrero", type="primary", use_container_width=True)

        if submitted:
            if not nombre.strip():
                st.error("El nombre del potrero es obligatorio.")
            else:
                db = get_session()
                try:
                    pot = Potrero(
                        nombre=nombre.strip(),
                        numero=numero.strip() or None,
                        hectareas=hectareas if hectareas > 0 else None,
                        notas=notas.strip() or None,
                    )
                    db.add(pot)
                    db.commit()
                    st.success(f"✅ Potrero '{nombre}' agregado.")
                    st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"Error: {e} (¿ya existe un potrero con ese nombre?)")
                finally:
                    db.close()

    df_pot = load_potreros()
    if df_pot.empty:
        st.info("Sin potreros registrados. Agregá uno arriba.")
    else:
        editable_table(
            df_pot,
            Potrero,
            {
                "Nombre": "nombre", "Número": "numero",
                "Hectáreas": "hectareas", "Notas": "notas",
            },
            key="edit_potreros",
            caption="✏️ Editá en la grilla. Marcá 🗑️ para borrar (elimina también sus asignaciones). Presioná Guardar.",
        )

# ── TAB 2: Asignaciones de hacienda ──────────────────────────────────────────
with tab2:
    df_pot2 = load_potreros()
    if df_pot2.empty:
        st.warning("Primero creá al menos un potrero en la pestaña anterior.")
    else:
        # Segmentación del stock por potrero (cabezas activas por categoría)
        st.subheader("📊 Stock segmentado por potrero")
        df_stock_pot = stock_por_potrero()
        if df_stock_pot.empty:
            st.info("Todavía no hay hacienda asignada a potreros. Asigná una abajo.")
        else:
            st.dataframe(df_stock_pot, use_container_width=True, hide_index=True)
            st.caption("Cabezas actualmente en cada potrero (asignaciones sin fecha de salida).")
        st.markdown("---")

        with st.expander("➕ Asignar hacienda a potrero", expanded=False):
            with st.form("form_asig", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    potrero_opciones = {row["Nombre"]: row["ID"] for _, row in df_pot2.iterrows()}
                    potrero_sel = st.selectbox("Potrero", list(potrero_opciones.keys()))
                    categoria = st.selectbox("Categoría", CATEGORIAS)
                with c2:
                    cantidad = st.number_input("Cantidad de animales", min_value=1, step=1)
                    fecha_entrada = st.date_input("Fecha de entrada", value=date.today())
                with c3:
                    fecha_salida = st.date_input("Fecha de salida (dejar en blanco si sigue)",
                                                  value=None)
                    notas = st.text_area("Notas", height=68)
                submitted2 = st.form_submit_button("💾 Guardar asignación", type="primary",
                                                    use_container_width=True)

            if submitted2:
                db = get_session()
                try:
                    asig = AsignacionPotrero(
                        potrero_id=potrero_opciones[potrero_sel],
                        fecha_entrada=fecha_entrada,
                        fecha_salida=fecha_salida,
                        categoria=categoria,
                        cantidad=int(cantidad),
                        notas=notas.strip() or None,
                    )
                    db.add(asig)
                    db.commit()
                    st.success(f"✅ Asignación guardada: {cantidad} {categoria} → {potrero_sel}")
                    st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"Error: {e}")
                finally:
                    db.close()

        # Tabla de asignaciones actuales (sin fecha de salida)
        df_asig = load_asignaciones()
        if not df_asig.empty:
            df_asig["Entrada"] = pd.to_datetime(df_asig["Entrada"])
            df_asig["Salida"] = pd.to_datetime(df_asig["Salida"], errors="coerce")

            st.subheader("Hacienda actualmente en potreros")
            actuales = df_asig[df_asig["Salida"].isna()].copy()
            if not actuales.empty:
                actuales["Entrada"] = actuales["Entrada"].dt.strftime("%d/%m/%Y")
                st.dataframe(actuales.drop(columns=["ID", "Salida"]), use_container_width=True,
                             hide_index=True)
            else:
                st.info("Sin asignaciones activas.")

            st.subheader("Historial completo de asignaciones")
            st.caption("El potrero se muestra pero no es editable acá (para cambiarlo, borrá y recreá la asignación).")
            editable_table(
                df_asig,
                AsignacionPotrero,
                {
                    "Categoría": "categoria", "Cantidad": "cantidad",
                    "Entrada": "fecha_entrada", "Salida": "fecha_salida", "Notas": "notas",
                },
                key="edit_asignaciones",
                disabled=["Potrero"],
                caption=None,
            )

# ── TAB 3: Movimientos de lotes entre potreros ───────────────────────────────
with tab3:
    df_pot3 = load_potreros()
    if df_pot3.empty:
        st.warning("Primero creá al menos un potrero en la pestaña 'Potreros'.")
    else:
        st.subheader("🔁 Mover un lote de un potrero a otro")
        stock_pot = stock_por_potrero()

        if stock_pot.empty:
            st.info("No hay hacienda asignada a potreros todavía. "
                    "Asigná una en la pestaña 'Asignaciones'.")
        else:
            nombre_a_id = {row["Nombre"]: row["ID"] for _, row in df_pot3.iterrows()}
            potreros_con_stock = stock_pot["Potrero"].tolist()

            c1, c2, c3 = st.columns(3)
            with c1:
                origen_nombre = st.selectbox("Potrero de origen", potreros_con_stock,
                                             key="mov_origen")
            # Categorías con stock activo en el potrero de origen
            fila = stock_pot[stock_pot["Potrero"] == origen_nombre].iloc[0]
            cats_disp = {
                col: int(fila[col]) for col in stock_pot.columns
                if col not in ("Potrero", "Total") and int(fila[col]) > 0
            }
            with c2:
                if cats_disp:
                    categoria_mov = st.selectbox(
                        "Categoría", list(cats_disp.keys()),
                        format_func=lambda c: f"{c} ({cats_disp[c]} disp.)",
                        key="mov_cat",
                    )
                    disp = cats_disp[categoria_mov]
                else:
                    categoria_mov, disp = None, 0
                    st.info("Sin stock en este potrero.")
            with c3:
                destino_opciones = [n for n in nombre_a_id if n != origen_nombre]
                destino_nombre = st.selectbox("Potrero de destino", destino_opciones,
                                              key="mov_destino")

            c4, c5 = st.columns(2)
            with c4:
                cantidad_mov = st.number_input(
                    "Cantidad a mover", min_value=1, max_value=max(disp, 1), step=1,
                    value=1, key="mov_cant",
                    help="Podés mover una parte del lote o el total disponible.",
                )
            with c5:
                fecha_mov = st.date_input("Fecha del movimiento", value=date.today(),
                                          key="mov_fecha")

            tipo_mov = st.radio("Tipo de movimiento",
                                ["Directo", "Después de trabajo a corral"],
                                horizontal=True, key="mov_tipo")
            trabajo_id = None
            if tipo_mov == "Después de trabajo a corral":
                df_trab = load_trabajos()
                if df_trab.empty:
                    st.info("No hay trabajos a corral registrados para vincular. "
                            "Se guardará como movimiento post-corral sin vínculo.")
                else:
                    df_trab["Fecha"] = pd.to_datetime(df_trab["Fecha"])
                    opciones_trab = {
                        f"{r['Fecha'].strftime('%d/%m/%Y')} · {r['Tipo de Trabajo']}": int(r["ID"])
                        for _, r in df_trab.head(50).iterrows()
                    }
                    trab_sel = st.selectbox("Trabajo a corral vinculado",
                                            list(opciones_trab.keys()), key="mov_trab")
                    trabajo_id = opciones_trab[trab_sel]

            notas_mov = st.text_input("Notas (opcional)", key="mov_notas")

            if st.button("🔁 Registrar movimiento", type="primary", key="mov_btn"):
                if not categoria_mov:
                    st.error("El potrero de origen no tiene stock para mover.")
                else:
                    try:
                        registrar_movimiento_potrero(
                            origen_id=nombre_a_id[origen_nombre],
                            destino_id=nombre_a_id[destino_nombre],
                            categoria=categoria_mov,
                            cantidad=int(cantidad_mov),
                            fecha=fecha_mov,
                            tipo="post-corral" if tipo_mov.startswith("Después") else "directo",
                            trabajo_corral_id=trabajo_id,
                            notas=notas_mov.strip() or None,
                        )
                        st.success(
                            f"✅ Movimiento: {int(cantidad_mov)} {categoria_mov} — "
                            f"{origen_nombre} → {destino_nombre}"
                        )
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Error al registrar el movimiento: {e}")

        st.markdown("---")
        st.subheader("Historial de movimientos")
        df_mov = load_movimientos_potrero()
        if df_mov.empty:
            st.info("Sin movimientos registrados todavía.")
        else:
            df_mov["Fecha"] = pd.to_datetime(df_mov["Fecha"]).dt.strftime("%d/%m/%Y")
            st.dataframe(df_mov.drop(columns=["ID"]), use_container_width=True,
                         hide_index=True)
            st.caption("El historial es un registro de auditoría. Para corregir el stock, "
                       "ajustá las asignaciones en la pestaña 'Asignaciones'.")
