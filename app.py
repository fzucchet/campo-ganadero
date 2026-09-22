import streamlit as st
import os
from dotenv import load_dotenv
from database.connection import init_db

load_dotenv()

st.set_page_config(
    page_title="Campo Ganadero",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inicializar base de datos ─────────────────────────────────────────────────
init_db()


# ── Autenticación simple ──────────────────────────────────────────────────────
def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.title("🐄 Sistema de Gestión Ganadera")
    st.markdown("---")
    col1, col2, col3 = st.columns([1.5, 1, 1.5])
    with col2:
        st.markdown("### Ingresar")
        pwd = st.text_input("Contraseña", type="password", key="login_pwd")
        if st.button("Entrar", use_container_width=True, type="primary"):
            if pwd == os.getenv("APP_PASSWORD", "campo123"):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
    return False


if not check_password():
    st.stop()

# ── Página principal ──────────────────────────────────────────────────────────
st.title("🐄 Campo Ganadero")
st.markdown("### Sistema de Gestión Integral")
st.markdown("---")

modulos = [
    ("📊", "Dashboard", "Resumen general y gráficos del año"),
    ("💰", "Ventas y Cargas", "Ventas de hacienda: fechas, categorías, kgs y precios"),
    ("💀", "Mortandad", "Registro de bajas con causa y potrero"),
    ("🔧", "Trabajos a Corral", "Sanidad, pesajes, tactos y vacunaciones"),
    ("📦", "Inventario", "Stock actual y movimientos de hacienda"),
    ("💸", "Gastos", "Costos del campo por categoría"),
    ("🐾", "Reproducción", "Tactos, partos y destetes"),
    ("🌿", "Potreros", "Gestión de potreros y asignación de hacienda"),
    ("🤖", "Asistente IA", "Preguntale a OpenAI sobre tus datos"),
]

cols = st.columns(3)
for i, (icon, nombre, desc) in enumerate(modulos):
    with cols[i % 3]:
        st.info(f"**{icon} {nombre}**\n\n{desc}")

# ── Sidebar logout ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    if st.button("🔒 Cerrar sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
