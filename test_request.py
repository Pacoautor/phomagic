import requests

url = "https://www.phomagic.com/api/job/validate/"
payload = {
    "category": "Moda",
    "subcategory": "Camisetas y Polos",
    "views": ["estirada", "plegada"],
    "options": {
        "size": {"width": 1280, "height": 1920},
        "background_hex": "#ffffff",
        "shadow": {"enabled": True, "mode": "multiply", "opacity": 0.43, "angle": 90, "distance": 18, "spread": 0, "size": 21},
        "logo": True,
        "neck_label": False
    },
    "image_url": "https://ejemplo.com/foto.jpg"
}
resp = requests.post(url, json=payload)
print(resp.json())
