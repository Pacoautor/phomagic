
# catalog/catalog_config.py

CATALOG = {
    "Moda": {
        "Camisetas y Polos": {
            "views": [
                {"id": "estirada", "label": "Estirada"},
                {"id": "plegada", "label": "Plegada"},
                {"id": "maniqui_invisible", "label": "Maniquí invisible"}
            ],
            "sizes_px": [
                {"width": 1280, "height": 1920},
                {"width":  720, "height":  800},
                {"width":  420, "height":  540},
            ],
        }
    }
}

SHADOW_PRESET_PHOTOSHOP = {
    "mode": "multiply",   # “Multiplicar”
    "opacity": 0.43,      # 43 %
    "angle": 90,          # 90°
    "distance": 18,       # px
    "spread": 0,          # %
    "size": 21            # px
}

DEFAULTS = {
    "background_hex": "#FFFFFF",
    "shadow": {
        "enabled": True,
        **SHADOW_PRESET_PHOTOSHOP
    },
    "logo": True,
    "neck_label": False
}
