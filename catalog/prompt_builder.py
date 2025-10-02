# catalog/prompt_builder.py

from textwrap import dedent

def _shadow_human(shadow: dict) -> str:
    if not shadow or not shadow.get("enabled", False):
        return "sin sombra."
    # ejemplo humano con tus valores tipo Photoshop
    return (
        f"sombra realista modo {shadow.get('mode','multiply')}, "
        f"opacidad {int(shadow.get('opacity',0.43)*100)}%, "
        f"ángulo {shadow.get('angle',90)}°, "
        f"distancia {shadow.get('distance',18)}px, "
        f"tamaño {shadow.get('size',21)}px."
    )

def _common_header(size, bg_hex, shadow):
    return dedent(f"""
    Fotografía de estudio profesional, luz uniforme, fondo {bg_hex},
    {_shadow_human(shadow)}
    Mantén colores, estampados y detalles fieles al original; no inventes ni elimines.
    Salida exacta {size['width']}x{size['height']} px, centrado y simetría correctos.
    """)

def _view_estirada(size, bg_hex, shadow):
    body = dedent("""
    CAMISETA/POLO ESTIRADA
    - Prenda plana, extendida vertical.
    - Mangas rectas hacia abajo, sin pliegues ni dobleces.
    - Cuello en su forma natural, erguido.
    - Caída plana, sin volumen interno.
    """)
    return _common_header(size, bg_hex, shadow) + "\n" + body

def _view_plegada(size, bg_hex, shadow):
    body = dedent("""
    CAMISETA/POLO PLEGADA
    - Planchar: sin arrugas, textura nítida.
    - Plegado final cuadrado: dobladillo al cuello; mangas hacia el centro; pliegue horizontal para formar cuadrado compacto.
    - Presentación ordenada, lista para empaquetado.
    """)
    return _common_header(size, bg_hex, shadow) + "\n" + body

def _view_maniqui_invisible(size, bg_hex, shadow):
    body = dedent("""
    CAMISETA/POLO MANIQUÍ INVISIBLE
    - Volumen 3D realista como si hubiera torso invisible.
    - Mangas cilíndricas con volumen natural; hombros definidos; laterales con caída natural.
    - Sin arrugas; textura y bordes nítidos.
    """)
    return _common_header(size, bg_hex, shadow) + "\n" + body

VIEW_PROMPTS = {
    "estirada": _view_estirada,
    "plegada": _view_plegada,
    "maniqui_invisible": _view_maniqui_invisible,
}

def build_prompts(job: dict):
    """Devuelve una lista de tareas por vista con el prompt generado."""
    opts = job["client_options"]
    size = opts["size_px"]
    bg_hex = opts["background"]["hex"]
    shadow = opts.get("shadow", {})
    tasks = []
    for v in job["views_requested"]:
        vid = v["id"]
        fn = VIEW_PROMPTS.get(vid)
        if not fn:
            continue
        tasks.append({
            "view_id": vid,
            "prompt": fn(size, bg_hex, shadow),
        })
    return tasks
