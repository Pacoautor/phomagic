# catalog/openai_client.py
import os
from openai import OpenAI

def get_client() -> OpenAI:
    """
    Crea el cliente usando la variable de entorno OPENAI_API_KEY.
    En Render: Config Vars → OPENAI_API_KEY=tu_clave
    """
    # La lib usa por defecto OPENAI_API_KEY del entorno.
    return OpenAI()
