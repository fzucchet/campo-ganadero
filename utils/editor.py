"""
Componente reutilizable de edición de tablas.

Muestra una tabla editable (estilo planilla) con `st.data_editor` y un botón
para guardar los cambios en la base de datos. Detecta qué filas cambiaron
comparando contra los valores originales y aplica sólo los UPDATE necesarios.
"""
import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import Integer, Float, Date, String

from database.connection import get_session


def _coerce(value, col_type):
    """Convierte un valor de la tabla editable al tipo Python del modelo."""
    # Valores vacíos → None
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    if isinstance(value, pd.Timestamp) and pd.isna(value):
        return None

    if isinstance(col_type, Integer):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if isinstance(col_type, Float):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    if isinstance(col_type, Date):
        if isinstance(value, pd.Timestamp):
            return value.date()
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            return pd.to_datetime(value).date()
        return None
    # String / Text
    return str(value)


def _is_equal(a, b) -> bool:
    """Compara dos valores tolerando None/NaN y diferencias de tipo menores."""
    a_na = a is None or (isinstance(a, float) and pd.isna(a)) or (isinstance(a, pd.Timestamp) and pd.isna(a))
    b_na = b is None or (isinstance(b, float) and pd.isna(b)) or (isinstance(b, pd.Timestamp) and pd.isna(b))
    if a_na and b_na:
        return True
    if a_na != b_na:
        return False
    # Fechas
    if isinstance(a, (datetime.date, pd.Timestamp)) or isinstance(b, (datetime.date, pd.Timestamp)):
        try:
            return pd.Timestamp(a).date() == pd.Timestamp(b).date()
        except (ValueError, TypeError):
            return str(a) == str(b)
    # Numéricos
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return str(a) == str(b)


def _auto_column_config(model, column_map, disabled):
    """Genera column_config a partir de los tipos de columna del modelo."""
    cols = {c.name: c.type for c in model.__table__.columns}
    config = {"ID": None}  # ocultar la columna ID en la grilla (se usa sólo internamente)
    for df_col, attr in column_map.items():
        col_type = cols.get(attr)
        is_disabled = df_col in disabled
        if isinstance(col_type, Date):
            config[df_col] = st.column_config.DateColumn(df_col, format="DD/MM/YYYY", disabled=is_disabled)
        elif isinstance(col_type, Integer):
            config[df_col] = st.column_config.NumberColumn(df_col, step=1, disabled=is_disabled)
        elif isinstance(col_type, Float):
            config[df_col] = st.column_config.NumberColumn(df_col, disabled=is_disabled)
        else:
            config[df_col] = st.column_config.TextColumn(df_col, disabled=is_disabled)
    return config


def editable_table(df, model, column_map, key, disabled=None, extra_config=None,
                   derive=None,
                   caption="✏️ Editá directamente en la grilla. Marcá 🗑️ para borrar filas. Presioná Guardar para aplicar."):
    """
    Renderiza una tabla editable y persiste los cambios en la base.

    Parámetros
    ----------
    df : pd.DataFrame
        Debe incluir la columna 'ID' con la clave primaria de cada fila.
    model : clase del modelo SQLAlchemy (con atributo `id`).
    column_map : dict {nombre_columna_df: nombre_atributo_modelo}
        Sólo las columnas listadas aquí se pueden persistir.
    key : str
        Clave única para el widget (usar una por tabla/página).
    disabled : list[str] | None
        Columnas visibles pero no editables (ej. computadas o de join).
    extra_config : dict | None
        Overrides de `column_config` de Streamlit.
    derive : dict | None
        {atributo_modelo: callable(fila_editada) -> valor}. Se aplica al guardar
        para calcular campos a partir de otros (ej. categoría según el tipo).
    caption : str | None
        Texto de ayuda mostrado sobre la grilla (None para ocultarlo).
    """
    if df.empty:
        st.info("Sin datos para editar.")
        return

    disabled = list(disabled or [])
    original = df.reset_index(drop=True).copy()

    if caption:
        st.caption(caption)

    # Columna de borrado al inicio de la grilla
    grid = original.copy()
    grid.insert(0, "🗑️", False)

    column_config = _auto_column_config(model, column_map, disabled)
    if extra_config:
        column_config.update(extra_config)
    column_config["🗑️"] = st.column_config.CheckboxColumn(
        "🗑️", help="Marcá para eliminar esta fila al guardar", default=False,
    )

    edited = st.data_editor(
        grid,
        key=key,
        num_rows="fixed",
        use_container_width=True,
        hide_index=True,
        disabled=["ID", *disabled],
        column_config=column_config,
    )

    save_clicked = st.button("💾 Guardar cambios", type="primary", key=f"{key}_save")

    # Filas marcadas para eliminar (según el estado actual de la grilla)
    marcadas = [i for i in range(len(edited)) if bool(edited.iloc[i]["🗑️"])]
    confirm_key = f"{key}_confirm_delete"

    # Si se pidió guardar y hay filas marcadas, activar la confirmación
    if save_clicked and marcadas:
        st.session_state[confirm_key] = True

    proceder = save_clicked and not marcadas

    if st.session_state.get(confirm_key) and marcadas:
        st.warning(
            f"⚠️ Vas a **eliminar {len(marcadas)} fila(s)**. Esta acción no se puede deshacer."
        )
        c1, c2 = st.columns(2)
        confirmar = c1.button("🗑️ Sí, eliminar", type="primary", key=f"{key}_confirm_yes")
        cancelar = c2.button("Cancelar", key=f"{key}_confirm_no")
        if cancelar:
            st.session_state.pop(confirm_key, None)
            st.rerun()
        proceder = confirmar

    if proceder:
        st.session_state.pop(confirm_key, None)
        col_types = {c.name: c.type for c in model.__table__.columns}
        db = get_session()
        try:
            filas_cambiadas = 0
            campos_cambiados = 0
            filas_eliminadas = 0
            for i in range(len(edited)):
                row_id = int(original.iloc[i]["ID"])
                obj = db.query(model).filter(model.id == row_id).first()
                if obj is None:
                    continue

                # Eliminación: si la casilla está marcada, borrar y saltar
                if bool(edited.iloc[i]["🗑️"]):
                    db.delete(obj)
                    filas_eliminadas += 1
                    continue

                fila_modificada = False
                for df_col, attr in column_map.items():
                    if df_col in disabled or df_col == "ID":
                        continue
                    old_val = original.iloc[i][df_col]
                    new_val = edited.iloc[i][df_col]
                    if _is_equal(old_val, new_val):
                        continue
                    setattr(obj, attr, _coerce(new_val, col_types.get(attr)))
                    campos_cambiados += 1
                    fila_modificada = True

                # Campos derivados (ej. categoría según el tipo elegido)
                if derive:
                    for attr, fn in derive.items():
                        calc_val = fn(edited.iloc[i])
                        if not _is_equal(getattr(obj, attr), calc_val):
                            setattr(obj, attr, _coerce(calc_val, col_types.get(attr)))
                            campos_cambiados += 1
                            fila_modificada = True

                if fila_modificada:
                    filas_cambiadas += 1

            if campos_cambiados or filas_eliminadas:
                db.commit()
                partes = []
                if campos_cambiados:
                    partes.append(f"{campos_cambiados} campo(s) en {filas_cambiadas} fila(s) actualizados")
                if filas_eliminadas:
                    partes.append(f"{filas_eliminadas} fila(s) eliminada(s)")
                st.success("✅ Guardado: " + "; ".join(partes) + ".")
                st.rerun()
            else:
                st.info("No hay cambios para guardar.")
        except Exception as e:
            db.rollback()
            st.error(f"Error al guardar: {e}")
        finally:
            db.close()
