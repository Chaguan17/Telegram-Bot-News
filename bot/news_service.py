import asyncio
import hashlib

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
    "https://www.criptonoticias.com/feed/",
    "https://www.coindesk.com/arc/outboundfeeds/rss?outputType=xml",
    "https://cryptonews.com/news/feed/",
    "https://www.investing.com/rss/news_25.rss"
]


def hash_string(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _entry_value(entry, key: str) -> str:
    if isinstance(entry, dict):
        return entry.get(key, "")
    return getattr(entry, key, "")


def filter_news_entries(feeds, *, keywords=None, per_feed_limit: int = 5, max_results: int = 3) -> list:
    """Filter already-fetched RSS entries into high-impact bot messages.

    `feeds` is an iterable of `(url, entries)` pairs. This keeps RSS fetching
    separate from scoring so different runtimes can provide entries their own way.
    """
    keywords = keywords or KEYWORDS
    encontradas = []

    for url, entries in feeds:
        for entry in list(entries)[:per_feed_limit]:
            titulo = _entry_value(entry, "title")
            link = _entry_value(entry, "link")
            score = sum(peso for pal, peso in keywords.items() if pal in titulo.lower())

            if score >= 4:
                nivel = "🔴 IMPACTO" if score >= 7 else "🟡 INFO"
                msg = f"{nivel}\n📰 *{titulo}*\n🔗 [Ver noticia]({link})"
                encontradas.append({
                    "hash": hash_string(titulo[:90]),
                    "message": msg,
                    "score": score,
                })

    encontradas.sort(key=lambda x: x["score"], reverse=True)
    return encontradas[:max_results]


def buscar_noticias_with_loader(feed_loader, feeds=None) -> list:
    fetched_feeds = []

    for url in feeds or RSS_FEEDS:
        try:
            fetched_feeds.append((url, feed_loader(url)))
        except Exception as e:
            print(f"Error parsing feed {url}: {e}")
            continue

    return filter_news_entries(fetched_feeds)


async def buscar_noticias_with_async_loader(feed_loader, feeds=None) -> list:
    """Async equivalent of buscar_noticias_with_loader for Worker-friendly fetchers."""
    selected_feeds = list(feeds or RSS_FEEDS)

    async def load(url):
        try:
            return url, await feed_loader(url)
        except Exception as e:
            print(f"Error parsing feed {url}: {e}")
            return url, None

    loaded = await asyncio.gather(*(load(url) for url in selected_feeds))
    return filter_news_entries((url, entries) for url, entries in loaded if entries is not None)
