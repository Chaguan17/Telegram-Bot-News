import requests
import feedparser

from bot.market_service import DEFAULT_TIMEZONE, obtener_estado_mercados
from bot.news_service import KEYWORDS, RSS_FEEDS, buscar_noticias_with_loader, hash_string
from bot.price_service import format_prices

tz = DEFAULT_TIMEZONE


def obtener_precios() -> str:
    try:
        # Volvemos a la API principal pero con símbolos específicos y User-Agent
        url = "https://api.binance.com/api/v3/ticker/price?symbols=[\"BTCUSDT\",\"ETHUSDT\",\"BNBUSDT\"]"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return f"❌ Binance (Error {response.status_code}). Inténtalo en unos minutos."
            
        return format_prices(response.json())
    except Exception as e:
        print(f"Error Binance: {e}")
        return "❌ Error al conectar con Binance API."


def buscar_noticias() -> list:
    """Devuelve una lista de diccionarios con noticias de alto impacto."""
    return buscar_noticias_with_loader(lambda url: feedparser.parse(url).entries)
