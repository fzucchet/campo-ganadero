"""
Parser propio (sin IA / sin tokens) para cargar registros desde texto libre.

Interpreta frases como:
  - "se encontró un ternero muerto en el potrero 63"
  - "se cargaron 100 terneros machos, 20.000 kgs a 1500 el kilo"
  - "compré 50 vacas por 30.000.000"
  - "vacuné 200 terneras con aftosa"

Devuelve un dict con el tipo de registro detectado y los campos, para que la
página muestre una vista previa editable antes de guardar. Nada se guarda sin
confirmación del usuario.
"""
import re
from datetime import date, timedelta

# (plural, singular) — el singular es prefijo del plural, sirve para detectar ambos.
CATEGORIAS_ANIMALES = [
    ("terneros", "ternero"),
    ("terneras", "ternera"),
    ("vaquillas", "vaquilla"),
    ("vacas", "vaca"),
    ("novillos", "novillo"),
    ("toros", "toro"),
    ("bueyes", "buey"),
]

# Productos y acciones de trabajo a corral (canónico → alias detectables en el texto).
ACCIONES_TRABAJO = [
    ("tacto", ["tactos", "tacto", "diagnóstico de preñez", "preñez"]),
    ("pesaje", ["pesaje", "pesé", "pesaron", "pesar"]),
    ("aparte / separación", ["aparte", "separación", "separacion"]),
    ("destete", ["destete", "desteté", "destetaron"]),
    ("descorne", ["descorne", "descornar"]),
    ("carimbo / marcación", ["carimbo", "marcación", "marcacion"]),
    ("castración", ["castración", "castracion", "castrar"]),
]
PRODUCTOS_TRABAJO = [
    ("aftosa", ["aftosa"]),
    ("brucelosis", ["brucelosis"]),
    ("mancha", ["mancha"]),
    ("polibac", ["polibac"]),
    ("ivermectina", ["ivermectina", "invermectina"]),
    ("vitamina", ["vitaminas", "vitamina"]),
    ("cobre", ["cobre"]),
    ("ricobendazol", ["ricobendazol"]),
    ("pour on", ["pour on"]),
    ("suplenut", ["suplenut"]),
    ("desparasitación", ["desparasit"]),
]

TIPOS_MOV_INVENTARIO = ["compra", "nacimiento", "destete", "ajuste de inventario", "otro ingreso"]


def _a_numero(token: str) -> float | None:
    """Convierte un token numérico en formato argentino ('20.000', '1.500,50') a float."""
    if not token:
        return None
    t = token.strip().replace(" ", "")
    if not re.search(r"\d", t):
        return None
    tiene_punto = "." in t
    tiene_coma = "," in t
    if tiene_punto and tiene_coma:
        # '.' = miles, ',' = decimal
        t = t.replace(".", "").replace(",", ".")
    elif tiene_coma:
        # ',' decimal si quedan 1-2 dígitos, si no son miles
        if len(t.split(",")[-1]) == 3:
            t = t.replace(",", "")
        else:
            t = t.replace(",", ".")
    elif tiene_punto:
        # '.' de miles si el último grupo tiene 3 dígitos
        if len(t.split(".")[-1]) == 3:
            t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def _detectar_categoria(texto: str) -> tuple[str, str] | None:
    """Devuelve (plural, singular) de la primera categoría de animal encontrada."""
    for plural, singular in CATEGORIAS_ANIMALES:
        if re.search(rf"\b{singular}", texto):
            return plural, singular
    if re.search(r"\bmacho", texto):
        return "terneros", "ternero"
    if re.search(r"\bhembra", texto):
        return "terneras", "ternera"
    return None


def _detectar_fecha(texto: str) -> date:
    hoy = date.today()
    if "anteayer" in texto:
        return hoy - timedelta(days=2)
    if "ayer" in texto:
        return hoy - timedelta(days=1)
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", texto)
    if m:
        d, mes, anio = int(m.group(1)), int(m.group(2)), m.group(3)
        if anio:
            a = int(anio)
            if a < 100:
                a += 2000
        else:
            a = hoy.year
        try:
            return date(a, mes, d)
        except ValueError:
            return hoy
    return hoy


def _detectar_potrero(texto: str) -> str | None:
    m = re.search(r"potrero\s+([a-záéíóúñ0-9]+)", texto)
    if m:
        return m.group(1)
    m = re.search(r"\ben el\s+([0-9]+)\b", texto)
    if m:
        return m.group(1)
    return None


def _extraer_kgs(texto: str) -> float | None:
    m = re.search(r"([\d.,]+)\s*(?:kgs|kg|kilos|kilo|k)\b", texto)
    return _a_numero(m.group(1)) if m else None


def _extraer_precio(texto: str, kgs: float | None) -> float | None:
    """Devuelve el precio TOTAL. Si el texto indica precio por kilo, lo multiplica por kgs."""
    # Precio por kilo: "a 1500 el kilo", "a $1500/kg", "1500 por kilo", "$5650 el kg"
    m = re.search(r"([\d.,]+)\s*(?:\$|pesos)?\s*(?:/|por|el)\s*(?:kilos?|kgs?)\b", texto)
    if not m:
        m = re.search(r"([\d.,]+)\s*(?:\$|pesos)?\s*/\s*(?:kg|kilo)\b", texto)
    if m:
        por_kilo = _a_numero(m.group(1))
        if por_kilo is not None and kgs:
            return por_kilo * kgs
        return por_kilo
    # Precio total: "$30.000.000", "por 30000000", "30.000.000 pesos", "total 30000000"
    m = re.search(r"(?:total|por|a)\s*\$?\s*([\d.,]+)\s*(?:\$|pesos)?", texto)
    if m and _a_numero(m.group(1)) and _a_numero(m.group(1)) > 1000:
        return _a_numero(m.group(1))
    m = re.search(r"\$\s*([\d.,]+)", texto)
    if m:
        return _a_numero(m.group(1))
    m = re.search(r"([\d.,]+)\s*(?:\$|pesos)\b", texto)
    if m:
        return _a_numero(m.group(1))
    return None


def _extraer_cantidad(texto: str) -> int | None:
    # Número justo antes de una categoría o de "cabezas".
    roots = "|".join(s for _, s in CATEGORIAS_ANIMALES)
    m = re.search(rf"(\d[\d.,]*)\s+(?:{roots}|cabezas|cab\b|animales)", texto)
    if not m:
        m = re.search(r"(\d[\d.,]*)\s*(?:cabezas|cab)\b", texto)
    if m:
        n = _a_numero(m.group(1))
        return int(n) if n is not None else None
    # "un/una" = 1
    if re.search(r"\bun[ao]?\b", texto):
        return 1
    return None


def _detectar_tipo_trabajo(texto: str) -> str | None:
    """Combina todas las acciones y productos detectados (ej: 'ivermectina + suplenut')."""
    encontrados: list[str] = []
    for canonico, alias in ACCIONES_TRABAJO + PRODUCTOS_TRABAJO:
        if any(a in texto for a in alias) and canonico not in encontrados:
            encontrados.append(canonico)
    return " + ".join(encontrados) if encontrados else None


def _encontrar_anclas(texto: str) -> list[tuple[int, int, str, str]]:
    """Ubica los grupos de animales del tipo '<nro> <categoría>' (o 'un/una <categoría>').

    Devuelve una lista de (posición, cantidad, plural, singular) ordenada por posición.
    """
    anclas: list[tuple[int, int, str, str]] = []
    for plural, singular in CATEGORIAS_ANIMALES:
        for m in re.finditer(rf"\b(\d[\d.,]*|unos|unas|una|un)\s+{singular}", texto):
            tok = m.group(1)
            if re.match(r"[\d.,]+$", tok):
                n = _a_numero(tok)
                cant = int(n) if n else 0
            else:
                cant = 1
            anclas.append((m.start(), cant, plural, singular))
    anclas.sort(key=lambda x: x[0])
    return anclas


def _build_mortandad(seg: str, seg_orig: str, fecha: date) -> dict:
    cat = _detectar_categoria(seg)
    singular = cat[1] if cat else "otro"
    potrero = _detectar_potrero(seg)
    return {
        "tipo": "mortandad",
        "campos": {
            "fecha": fecha,
            "categoria": singular,
            "potrero": potrero or "",
            "descripcion": seg_orig.strip(),
        },
        "confianza": "alta" if cat else "media",
        "resumen": f"Baja de {singular}" + (f" en potrero {potrero}" if potrero else ""),
    }


def _build_inventario(seg: str, seg_orig: str, fecha: date) -> dict:
    cat = _detectar_categoria(seg)
    plural = cat[0] if cat else "terneros"
    cantidad = _extraer_cantidad(seg) or 0
    if "compr" in seg:
        tipo_mov = "compra"
    elif re.search(r"nacier|nacimiento|naci", seg):
        tipo_mov = "nacimiento"
    elif "ajuste" in seg:
        tipo_mov = "ajuste de inventario"
    else:
        tipo_mov = "otro ingreso"
    kgs = _extraer_kgs(seg)
    monto = _extraer_precio(seg, kgs)
    return {
        "tipo": "inventario",
        "campos": {
            "fecha": fecha,
            "categoria": plural,
            "cantidad": cantidad,
            "tipo_movimiento": tipo_mov,
            "monto": monto,
            "notas": seg_orig.strip(),
        },
        "confianza": "alta" if cat and cantidad else "media",
        "resumen": f"{tipo_mov.capitalize()} de {cantidad} {plural}",
    }


def _build_venta(seg: str, seg_orig: str, fecha: date) -> dict:
    cat = _detectar_categoria(seg)
    plural = cat[0] if cat else "terneros"
    cantidad = _extraer_cantidad(seg) or 0
    kgs = _extraer_kgs(seg)
    precio = _extraer_precio(seg, kgs)
    return {
        "tipo": "venta",
        "campos": {
            "fecha": fecha,
            "categoria": plural,
            "cantidad": cantidad,
            "kgs": kgs,
            "precio_total": precio or 0.0,
            "notas": seg_orig.strip(),
        },
        "confianza": "alta" if (cat and cantidad and precio) else "media",
        "resumen": f"Venta de {cantidad} {plural}"
                   + (f", {kgs:.0f} kg" if kgs else "")
                   + (f", ${precio:,.0f}".replace(",", ".") if precio else ""),
    }


def _build_trabajo(seg: str, seg_orig: str, fecha: date, tipo_global: str | None = None) -> dict:
    tipo_local = _detectar_tipo_trabajo(seg)
    tipo_trab = tipo_local or tipo_global or "sanidad"
    return {
        "tipo": "trabajo",
        "campos": {
            "fecha": fecha,
            "categoria": "Sanidad",
            "tipo_trabajo": tipo_trab,
            "animales": seg_orig.strip(),
            "resultado": "",
            "notas": "",
        },
        "confianza": "alta" if tipo_local else ("media" if tipo_global else "baja"),
        "resumen": f"Trabajo a corral: {tipo_trab}",
    }


def parse_texto(texto_original: str) -> list[dict]:
    """Interpreta el texto y devuelve una lista de registros {tipo, campos, confianza, resumen}.

    Para trabajos a corral con dos o más grupos de animales que tienen productos
    distintos (ej: '100 vacas con ivermectina y 50 terneros con ricobendazol'),
    devuelve un registro por grupo. En el resto de los casos devuelve un registro.
    """
    if not texto_original or not texto_original.strip():
        return []

    texto = texto_original.lower().strip()
    fecha = _detectar_fecha(texto)

    # ── Prioridad 1: Mortandad ────────────────────────────────────────────────
    if re.search(r"muert|muri|falleci|deceso", texto):
        return [_build_mortandad(texto, texto_original, fecha)]

    # ── Prioridad 2: Inventario (compra / nacimiento / ajuste) ────────────────
    if re.search(r"compr|nacier|nacimiento|\bnaci\b|ajuste|ingres|entraron", texto):
        return [_build_inventario(texto, texto_original, fecha)]

    # ── Prioridad 3: Venta / Carga ────────────────────────────────────────────
    if re.search(r"vend|venta|cargaron|cargu|carga|despach|salieron|remat", texto):
        anclas = _encontrar_anclas(texto)
        if len(anclas) >= 2:
            # Lote mixto: una sola venta con el total; la composición descuenta el stock.
            kgs_total = _extraer_kgs(texto)
            precio_total = _extraer_precio(texto, kgs_total) or 0.0
            comp_pairs: dict[str, int] = {}
            for _, cant, plural, _ in anclas:
                comp_pairs[plural] = comp_pairs.get(plural, 0) + cant
            total_cab = sum(comp_pairs.values())
            composicion = ",".join(f"{k}:{v}" for k, v in comp_pairs.items())
            comp_txt = " + ".join(f"{v} {k}" for k, v in comp_pairs.items())
            return [{
                "tipo": "venta",
                "campos": {
                    "fecha": fecha,
                    "categoria": "mixto",
                    "cantidad": total_cab,
                    "kgs": kgs_total,
                    "precio_total": precio_total,
                    "composicion": composicion,
                    "notas": f"{texto_original.strip()} · Lote mixto: {comp_txt} (pesados juntos, precio único)",
                },
                "confianza": "alta",
                "resumen": f"Venta lote mixto: {comp_txt}"
                           + (f", {kgs_total:.0f} kg" if kgs_total else "")
                           + (f", ${precio_total:,.0f}".replace(",", ".") if precio_total else ""),
            }]
        return [_build_venta(texto, texto_original, fecha)]

    # ── Prioridad 4: Trabajo a corral (puede dividirse en varios grupos) ──────
    tipo_global = _detectar_tipo_trabajo(texto)
    if tipo_global or re.search(r"trabaj|corral|vacun|sanid", texto):
        anclas = _encontrar_anclas(texto)
        if len(anclas) >= 2:
            segmentos = []
            for i, (start, *_rest) in enumerate(anclas):
                end = anclas[i + 1][0] if i + 1 < len(anclas) else len(texto)
                segmentos.append((texto[start:end], texto_original[start:end]))
            # Dividir sólo si al menos dos grupos tienen su propio producto/acción.
            con_producto = sum(1 for s_low, _ in segmentos if _detectar_tipo_trabajo(s_low))
            if con_producto >= 2:
                return [_build_trabajo(s_low, s_orig, fecha, tipo_global)
                        for s_low, s_orig in segmentos]
        return [_build_trabajo(texto, texto_original, fecha, tipo_global)]

    return []
