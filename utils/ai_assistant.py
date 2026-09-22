import os
from openai import OpenAI
from datetime import date
from database.connection import get_session
from database.models import (
    Venta, Mortandad, TrabajoCorral, Gasto,
    MovimientoInventario, Reproduccion, Potrero, IndiceReproductivo,
)

def _build_context() -> str:
    """Construye un resumen del campo para inyectar como contexto al modelo."""
    db = get_session()
    try:
        año = date.today().year

        # Ventas del año
        ventas = db.query(Venta).filter(
            Venta.fecha >= date(año, 1, 1)
        ).all()
        ventas_resumen = "\n".join(
            f"  - {v.fecha.strftime('%d/%m/%Y')}: {v.cantidad} {v.categoria}, "
            f"kgs={v.kgs or 'N/D'}, total=${v.precio_total:,.0f}"
            for v in ventas
        ) or "  Sin datos"

        # Mortandad del año
        bajas = db.query(Mortandad).filter(
            Mortandad.fecha >= date(año, 1, 1)
        ).all()
        bajas_resumen = "\n".join(
            f"  - {b.fecha.strftime('%d/%m/%Y')}: {b.categoria}, {b.descripcion or ''}"
            for b in bajas
        ) or "  Sin datos"

        # Trabajos recientes (últimos 20)
        trabajos = db.query(TrabajoCorral).order_by(TrabajoCorral.fecha.desc()).limit(20).all()
        trabajos_resumen = "\n".join(
            f"  - {t.fecha.strftime('%d/%m/%Y')}: {t.tipo_trabajo} — {t.animales or ''}"
            for t in trabajos
        ) or "  Sin datos"

        # Gastos del año
        gastos = db.query(Gasto).filter(
            Gasto.fecha >= date(año, 1, 1)
        ).all()
        total_gastos = sum(g.monto for g in gastos)
        gastos_resumen = f"  Total ${total_gastos:,.0f} — {len(gastos)} registros"

        # Tactos recientes
        tactos = db.query(Reproduccion).order_by(Reproduccion.fecha.desc()).limit(5).all()
        tactos_resumen = "\n".join(
            f"  - {t.fecha.strftime('%d/%m/%Y')}: {t.tipo}, preñadas={t.prenadas or 'N/D'}, vacías={t.vacias or 'N/D'}"
            for t in tactos
        ) or "  Sin datos"

        # Potreros
        potreros = db.query(Potrero).all()
        potreros_resumen = ", ".join(p.nombre for p in potreros) or "Sin potreros registrados"

        # Índices reproductivos históricos por temporada
        indices = db.query(IndiceReproductivo).all()
        indices_orden = sorted(
            indices,
            key=lambda r: (r.anio, 0 if r.temporada == "Otoño" else 1),
        )
        indices_resumen = "\n".join(
            f"  - {r.temporada} {r.anio}: total={r.total}, preñadas={r.prenadas} "
            f"({r.prenadas / r.total * 100:.1f}% preñez)"
            + (
                f", destete={r.destete} ({r.destete / r.prenadas * 100:.1f}% destete), "
                f"muertos parto-destete={r.muertos_parto_destete}"
                if r.destete else ""
            )
            for r in indices_orden
        ) or "  Sin datos"

        return f"""
DATOS ACTUALES DEL CAMPO (año {año}):

VENTAS / CARGAS:
{ventas_resumen}

MORTANDAD:
{bajas_resumen}

ÚLTIMOS TRABAJOS A CORRAL:
{trabajos_resumen}

GASTOS DEL AÑO:
{gastos_resumen}

REPRODUCCIÓN (registros recientes):
{tactos_resumen}

ÍNDICES REPRODUCTIVOS POR TEMPORADA (histórico):
{indices_resumen}

POTREROS DEL CAMPO:
{potreros_resumen}
"""
    finally:
        db.close()


SYSTEM_PROMPT = """Sos un asistente especializado en gestión ganadera para un campo en Argentina.
Tu rol es ayudar al productor a analizar sus datos, responder preguntas sobre su hacienda,
y dar recomendaciones prácticas basadas en los registros del sistema.

Respondé siempre en español rioplatense (vos, ustedes).
Sé conciso pero completo. Cuando hagas cálculos, mostrá los números claramente.
Si no tenés datos suficientes para responder con certeza, decilo.

Los datos del campo están incluidos en el contexto de cada mensaje.
"""


def get_ai_response(historia_chat: list[dict], pregunta: str) -> str:
    """
    Envía la pregunta a OpenAI con contexto de datos del campo.
    historia_chat: lista de dicts con keys 'role' ('user'/'assistant') y 'content'.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "⚠️ No se encontró la clave OPENAI_API_KEY. Configurala en las variables de entorno."

    try:
        client = OpenAI(api_key=api_key)
        contexto = _build_context()

        # Construir mensajes en formato OpenAI
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in historia_chat[:-1]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append(
            {"role": "user", "content": f"{contexto}\n\nPREGUNTA DEL PRODUCTOR:\n{pregunta}"}
        )

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Error al consultar OpenAI: {e}"
