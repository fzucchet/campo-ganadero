import streamlit as st


def require_auth():
    """Verifica que el usuario esté autenticado. Detiene la página si no lo está."""
    if not st.session_state.get("authenticated"):
        st.warning("⚠️ Por favor ingresá primero desde la página principal.")
        st.stop()
