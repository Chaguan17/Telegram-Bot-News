import time
import requests
import feedparser
import threading
import os
import json
import schedule
import telebot
import pytz
from datetime import datetime
from dotenv import load_dotenv

# ==========================================
# 1. CLASE PRINCIPAL: FINANCIAL BOT
# ==========================================
class FinancialBot:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.bot = telebot.TeleBot(self.token)
        self.archivo_usuarios = "usuarios.json"
        self.usuarios_activos = self._cargar_usuarios()
        self.noticias_enviadas = set()
        self.session = requests.Session()
        
        # Zona horaria maestra
        self.tz = pytz.timezone('Europe/Madrid')

        # Configuración
        self.keywords = {
    # === GEOPOLÍTICA Y MACRO (ALTO IMPACTO) ===
    'guerra': 5, 'conflicto': 4, 'misil': 5, 'ataque': 5,
    'sanciones': 4, 'petróleo': 3, 'brent': 3, 'tensión': 3,
    'escalada': 4, 'frontera': 3, 'taiwan': 4, 'israel': 4,
    'iran': 5, 'hormuz': 5, 'otan': 4, 'nato': 4,

    # === ENTORNO TRUMP (POLÍTICA USA) ===
    'trump': 5, 'aranceles': 5, 'tariffs': 5, 'discurso': 6,
    'habla': 6, 'decreto': 5, 'casa blanca': 4, 'white house': 4,
    'elecciones': 3, 'senado': 3, 'republicanos': 3,

    # === ECONOMÍA Y FED (MOVIMIENTO DE TASAS) ===
    'fed': 5, 'powell': 5, 'tasas': 4, 'rates': 4,
    'inflación': 5, 'inflation': 5, 'cpi': 5, 'ipc': 5,
    'pib': 4, 'gdp': 4, 'empleo': 3, 'fomc': 5,
    'recesión': 5, 'recession': 5,

    # === CRIPTOMONEDAS Y REGULACIÓN ===
    'sec': 5, 'gensler': 5, 'etf': 4, 'binance': 4,
    'cz': 3, 'coinbase': 3, 'regulacion': 4, 'prohibición': 5,
    'hack': 5, 'exploit': 5, 'listing': 4, 'delisting': 5,
    'halving': 4, 'spot': 3, 'cbdc': 4,

    # === TERMINOLOGÍA DE ALERTA (MULTIPLICADORES) ===
    'urgente': 6, 'última hora': 6, 'breaking': 6,
    'atención': 4, 'exclusiva': 4, 'confirmado': 5
}
        self.rss_feeds = [
            "https://es.beincrypto.com/feed/", # Perfil solicitado
            "https://es.cointelegraph.com/rss",
            "https://www.investing.com/rss/news_25.rss"
        ]

    # --- Persistencia ---
    def _cargar_usuarios(self):
        if not os.path.exists(self.archivo_usuarios): return set()
        try:
            with open(self.archivo_usuarios, "r") as f: return set(json.load(f))
        except: return set()

    def _guardar_usuarios(self):
        with open(self.archivo_usuarios, "w") as f: json.dump(list(self.usuarios_activos), f)

    # --- Precios (API Binance) ---
    def obtener_precios(self):
        try:
            url = "https://api.binance.com/api/v3/ticker/price"
            res = self.session.get(url, timeout=10).json()
            # Filtramos los símbolos que nos interesan
            p = {i['symbol']: float(i['price']) for i in res if i['symbol'] in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]}
            
            msg = "💰 **ACTUALIZACIÓN DE PRECIOS**\n\n"
            msg += f"• **BTC**: `${p['BTCUSDT']:,.2f}`\n"
            msg += f"• **ETH**: `${p['ETHUSDT']:,.2f}`\n"
            msg += f"• **BNB**: `${p['BNBUSDT']:,.2f}`"
            return msg
        except:
            return "❌ Error al conectar con Binance Square / API."

    # --- Mercados (Hora España) ---
    def obtener_estado_mercados(self):
        ahora_esp = datetime.now(self.tz)
        if ahora_esp.weekday() > 4:
            return "💤 **FIN DE SEMANA**\nBolsas cerradas. Criptos operando 24/7."

        h_decimal = ahora_esp.hour + ahora_esp.minute / 60.0
        texto = f"🌍 **MERCADOS (Hora España: {ahora_esp.strftime('%H:%M')})**\n\n"
        
        # Horarios exactos en hora peninsular
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

    # --- Noticias ---
    def buscar_noticias(self, manual=False, chat_id=None):
        encontradas = []
        for url in self.rss_feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    titulo = entry.title
                    if titulo[:90] in self.noticias_enviadas: continue
                    
                    score = sum(peso for pal, peso in self.keywords.items() if pal in titulo.lower())
                    if score >= 4 or "beincrypto" in url:
                        nivel = "🔴 IMPACTO" if score >= 7 else "🟡 INFO"
                        msg = f"{nivel}\n📰 *{titulo}*\n🔗 [Ver noticia]({entry.link})"
                        encontradas.append(msg)
                        self.noticias_enviadas.add(titulo[:90])
            except: continue

        for m in encontradas[:3]:
            if manual: self.bot.send_message(chat_id, m, parse_mode='Markdown')
            else: self.enviar_a_todos(m)

    def enviar_a_todos(self, mensaje):
        for uid in self.usuarios_activos:
            try: self.bot.send_message(uid, mensaje, parse_mode='Markdown')
            except: pass

# ==========================================
# 2. PLANIFICADOR (HORA ESPAÑA)
# ==========================================
asistente = FinancialBot()
bot = asistente.bot

def run_schedule():
    dias_semana = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    
    # 1. Alerta de Precios Cripto (Cada 1 hora)
    schedule.every(1).hours.do(lambda: asistente.enviar_a_todos(asistente.obtener_precios()))

    # 2. Aperturas de Mercados (Hora España)
    for d in dias_semana:
        getattr(schedule.every(), d).at("09:00").do(
            asistente.enviar_a_todos, "🇪🇺 **MERCADO ABIERTO**: Madrid y Londres inician sesión.")
        
        getattr(schedule.every(), d).at("15:30").do(
            asistente.enviar_a_todos, "🇺🇸 **WALL STREET ABIERTO**: Nueva York inicia. Máxima volatilidad y solapamiento.")

    # 3. Revisión de Noticias (Cada 15 min)
    schedule.every(15).minutes.do(asistente.buscar_noticias)

    while True:
        schedule.run_pending()
        time.sleep(1)

# ==========================================
# 3. COMANDOS TELEGRAM
# ==========================================
@bot.message_handler(commands=['start'])
def cmd_start(m):
    asistente.usuarios_activos.add(m.chat.id)
    asistente._guardar_usuarios()
    bot.reply_to(m, "🚀 **Bot Completo Activo**\n• /prices : Precios Cripto\n• /mercados : Estado de bolsas\n• /noticias : Buscar ahora")

@bot.message_handler(commands=['prices'])
def cmd_prices(m):
    bot.send_message(m.chat.id, asistente.obtener_precios(), parse_mode='Markdown')

@bot.message_handler(commands=['mercados'])
def cmd_mercados(m):
    bot.send_message(m.chat.id, asistente.obtener_estado_mercados(), parse_mode='Markdown')

@bot.message_handler(commands=['noticias'])
def cmd_noticias(m):
    asistente.buscar_noticias(manual=True, chat_id=m.chat.id)

if __name__ == "__main__":
    print("🤖 Bot funcionando con horario de España...")
    threading.Thread(target=run_schedule, daemon=True).start()
    bot.infinity_polling()