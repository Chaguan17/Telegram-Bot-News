import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# Añadir el root del proyecto al path para importar bot.services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import telebot

from bot.cron_service import run_news_cron
from bot.db import get_news_subscribers, is_news_sent, mark_news_sent, update_bot_health
from bot.services import buscar_noticias

token = os.getenv('TELEGRAM_TOKEN', '')
# Se inicializa globalmente para usar warm cache
bot = telebot.TeleBot(token)


def send_telegram_message(chat_id: int, message: str) -> None:
    bot.send_message(chat_id, message, parse_mode='Markdown')


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Punto de entrada para Vercel Cron. Debe configurarse en vercel.json"""
        print("Ejecutando Cron Job...")

        result = run_news_cron(
            buscar_noticias=buscar_noticias,
            get_news_subscribers=get_news_subscribers,
            is_news_sent=is_news_sent,
            mark_news_sent=mark_news_sent,
            send_message=send_telegram_message,
            update_bot_health=update_bot_health,
        )

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode('utf-8'))
