# bot/services.py
# Cleanup: Removed 'requests' as it's not supported in Cloudflare Workers.
# The worker now uses the provided async loaders (js.fetch).

from bot.market_service import obtener_estado_mercados

def obtener_precios() -> str:
    # Esta función ya no se usa directamente en el Worker (se usa el loader),
    # pero la dejamos como stub por si alguien la importa.
    return "❌ Función obsoleta. Use el loader asíncrono."

def buscar_noticias() -> list:
    # Esta función ya no se usa directamente en el Worker.
    return []
