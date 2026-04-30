import os
import sys
from http.server import BaseHTTPRequestHandler

# Añadir el root del proyecto al path para importar bot.services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.services import buscar_noticias
from bot.db import get_news_subscribers, is_news_sent, mark_news_sent, update_bot_health
import telebot

token = os.getenv('TELEGRAM_TOKEN', '')
# Se inicializa globalmente para usar warm cache
bot = telebot.TeleBot(token)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Punto de entrada para Vercel Cron. Debe configurarse en vercel.json"""
        print("Ejecutando Cron Job...")
        
        noticias_nuevas = buscar_noticias()
        usuarios = get_news_subscribers()
        
        enviadas_count = 0
        
        for noticia in noticias_nuevas:
            news_hash = noticia['hash']
            if not is_news_sent(news_hash):
                # La noticia es nueva, enviar a todos los usuarios
                for uid in usuarios:
                    try:
                        bot.send_message(uid, noticia['message'], parse_mode='Markdown')
                    except Exception as e:
                        print(f"Error enviando a {uid}: {e}")
                
                # Marcar como enviada
                mark_news_sent(news_hash)
                enviadas_count += 1
                
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        res = f'{{"status": "ok", "news_sent": {enviadas_count}}}'
        self.wfile.write(res.encode('utf-8'))
        
        # Registrar ejecución exitosa para el dashboard
        update_bot_health("ok")
