import sys
import os
import urllib.request

# Add the project root to sys.path so we can import our modules
sys.path.append(os.getcwd())

from bot.utils.rss_parser import parse_rss_custom
from bot.news_service import filter_news_entries, RSS_FEEDS, KEYWORDS

def test_extraction():
    print("--- Iniciando Simulacion de Extraccion con Logica de Produccion ---")
    print("-" * 50)
    
    fetched_feeds = []
    
    for url in RSS_FEEDS:
        print(f"--- Cargando feed: {url}")
        try:
            # Emulamos el fetch del worker
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_text = response.read().decode('utf-8', errors='ignore')
                entries = parse_rss_custom(xml_text)
                print(f"   OK: Se encontraron {len(entries)} entradas.")
                fetched_feeds.append((url, entries))
        except Exception as e:
            print(f"   ERROR: Cargando {url}: {e}")

    print("-" * 50)
    print("--- Aplicando Filtro de Impacto (Score >= 4) ---")
    
    # Usamos la lógica de filtrado real del bot
    resultados = filter_news_entries(fetched_feeds)
    
    if not resultados:
        print("WARN: No se encontraron noticias que superen el score de 4 en este ciclo.")
    else:
        print(f"INFO: Se encontraron {len(resultados)} noticias relevantes:")
        for idx, res in enumerate(resultados, 1):
            msg_clean = res['message'].encode('ascii', 'ignore').decode('ascii')
            print(f"\n{idx}. [{res['score']} pts] {msg_clean.split('\n')[1]}")
            # Verificamos qué palabras clave activaron el score
            titulo = msg_clean.split('\n')[1].lower()
            matches = [pal for pal in KEYWORDS if pal in titulo]
            print(f"   Matches: {', '.join(matches)}")

    print("-" * 50)
    print("DONE: Simulacion finalizada.")

if __name__ == "__main__":
    test_extraction()
