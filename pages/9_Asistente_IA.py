import streamlit as st
from utils.auth import require_auth
from utils.ai_assistant import get_ai_response
import os

st.set_page_config(page_title="Asistente IA | Campo Ganadero", page_icon="🤖", layout="wide")
require_auth()

st.title("🤖 Asistente IA")
st.markdown("Consultá sobre tus datos en lenguaje natural usando OpenAI")
st.markdown("---")

# Verificar API key
if not os.getenv("OPENAI_API_KEY"):
    st.warning(
        "⚠️ La variable **OPENAI_API_KEY** no está configurada. "
        "Obténela en https://platform.openai.com/api-keys y agregála en tu `.env` o en Railway."
    )

# Inicializar historial
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Ejemplos de preguntas
with st.expander("💡 Ejemplos de preguntas que podés hacer"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
- ¿Cuántas cabezas vendí este año?
- ¿Cuál fue el precio promedio por kilo en las últimas ventas?
- ¿Cuántos terneros murieron en julio?
- ¿Qué vacunas les di a los terneros?
        """)
    with col2:
        st.markdown("""
- ¿Cuántas vacas quedaron preñadas en el último tacto?
- ¿Cuáles son mis principales gastos del año?
- ¿Qué potreros tengo con hacienda actualmente?
- Dame un resumen del campo de este año
        """)

# Mostrar historial del chat
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input del usuario
pregunta = st.chat_input("¿Qué querés saber sobre el campo?")

if pregunta:
    # Mostrar pregunta
    with st.chat_message("user"):
        st.markdown(pregunta)

    # Agregar al historial
    st.session_state.chat_history.append({"role": "user", "content": pregunta})

    # Obtener respuesta
    with st.chat_message("assistant"):
        with st.spinner("Consultando OpenAI..."):
            respuesta = get_ai_response(st.session_state.chat_history, pregunta)
        st.markdown(respuesta)

    # Agregar respuesta al historial
    st.session_state.chat_history.append({"role": "assistant", "content": respuesta})

# Botón para limpiar chat
if st.session_state.chat_history:
    st.markdown("---")
    if st.button("🗑️ Limpiar conversación"):
        st.session_state.chat_history = []
        st.rerun()
