import requests
import feedparser
import pytz
import hashlib
from datetime import datetime

tz = pytz.timezone('Europe/Madrid')

KEYWORDS = {
    # Geopolítica
    'guerra': 5, 'conflicto': 4, 'misil': 5, 'ataque': 5,
    'sanciones': 4, 'petróleo': 3, 'brent': 3, 'tensión': 3,
    'escalada': 4, 'frontera': 3, 'taiwan': 4, 'israel': 4,
    'iran': 5, 'hormuz': 5, 'otan': 4, 'nato': 4,
    # Trump / Política
    'trump': 5, 'aranceles': 5, 'tariffs': 5, 'discurso': 6,
    'habla': 6, 'decreto': 5, 'casa blanca': 4, 'white house': 4,
    'elecciones': 3, 'senado': 3, 'republicanos': 3,
    # Economía
    'fed': 5, 'powell': 5, 'tasas': 4, 'rates': 4,
    'inflación': 5, 'inflation': 5, 'cpi': 5, 'ipc': 5,
    'pib': 4, 'gdp': 4, 'empleo': 3, 'fomc': 5,
    'recesión': 5, 'recession': 5,
    # Cripto
    'sec': 5, 'gensler': 5, 'etf': 4, 'binance': 4,
    'cz': 3, 'coinbase': 3, 'regulacion': 4, 'prohibición': 5,
    'hack': 5, 'exploit': 5, 'listing': 4, 'delisting': 5,
    'halving': 4, 'spot': 3, 'cbdc': 4,
    # Alerta
    'urgente': 6, 'última hora': 6, 'breaking': 6,
    'atención': 4, 'exclusiva': 4, 'confirmado': 5
}

RSS_FEEDS = [
    "https://es.beincrypto.com/feed/",
    "https://es.cointelegraph.com/rss",
    "https://www.investing.com/rss/news_25.rss"
]

def obtener_precios() -> str:
    try:
        # Volvemos a la API principal pero con símbolos específicos y User-Agent
        url = "https://api.binance.com/api/v3/ticker/price?symbols=[\"BTCUSDT\",\"ETHUSDT\",\"BNBUSDT\"]"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return f"❌ Binance (Error {response.status_code}). Inténtalo en unos minutos."
            
        res = response.json()
        p = {i['symbol']: float(i['price']) for i in res}
        
        msg = "💰 **ACTUALIZACIÓN DE PRECIOS**\n\n"
        msg += f"• **BTC**: `${p.get('BTCUSDT', 0):,.2f}`\n"
        msg += f"• **ETH**: `${p.get('ETHUSDT', 0):,.2f}`\n"
        msg += f"• **BNB**: `${p.get('BNBUSDT', 0):,.2f}`"
        return msg
    except Exception as e:
        print(f"Error Binance: {e}")
        return "❌ Error al conectar con Binance API."

def obtener_estado_mercados() -> str:
    ahora_esp = datetime.now(tz)
    if ahora_esp.weekday() > 4:
        return "💤 **FIN DE SEMANA**\nBolsas cerradas. Criptos operando 24/7."

    h_decimal = ahora_esp.hour + ahora_esp.minute / 60.0
    texto = f"🌍 **MERCADOS (Hora España: {ahora_esp.strftime('%H:%M')})**\n\n"
    
    fases = [
        ("🇯🇵 Asia (Tokio)", 1.0, 10.0),
        ("🇪🇺 Europa (Madrid/Londres)", 9.0, 17.35),
        ("🇺🇸 EE.UU. (Nueva York)", 15.5, 22.0)
    ]

    for nombre, abre, cierra in fases:
        estado = "🟢" if abre <= h_decimal <= cierra else "🔴"
        texto += f"{estado} **{nombre}**\n"

    if 15.5 <= h_decimal <= 17.58:
        texto += "\n🔥 **SOLAPAMIENTO DETECTADO**: Máximo volumen NYSE + Europa."
    
    return texto

def hash_string(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def buscar_noticias() -> list:
    """Devuelve una lista de diccionarios con noticias de alto impacto."""
    encontradas = []
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                titulo = entry.title
                score = sum(peso for pal, peso in KEYWORDS.items() if pal in titulo.lower())
                
                # Regla de negocio: score >= 4 o feed específico
                if score >= 4 or "beincrypto" in url:
                    nivel = "🔴 IMPACTO" if score >= 7 else "🟡 INFO"
                    msg = f"{nivel}\n📰 *{titulo}*\n🔗 [Ver noticia]({entry.link})"
                    news_hash = hash_string(titulo[:90])
                    
                    encontradas.append({
                        "hash": news_hash,
                        "message": msg,
                        "score": score
                    })
        except Exception as e:
            print(f"Error parsing feed {url}: {e}")
            continue

    # Ordenar por score desc y tomar top 3
    encontradas.sort(key=lambda x: x["score"], reverse=True)
    return encontradas[:3]
