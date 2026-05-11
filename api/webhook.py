import os
import sys
from functools import wraps
from http.server import BaseHTTPRequestHandler
import telebot

# Añadir el root del proyecto al path para importar bot.services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.command_service import (
    ban_response,
    ban_target,
    extract_broadcast_text,
    help_text,
    markets_response,
    news_messages,
    start_response,
    stats_response,
    subscription_response,
    timezone_callback_response,
    timezone_keyboard_payload,
)
from bot.services import obtener_precios, obtener_estado_mercados, buscar_noticias
from bot.db import add_user, set_news_enabled, get_user_stats, ban_user, get_all_users, log_command, get_user_timezone, set_user_timezone

token = os.getenv('TELEGRAM_TOKEN', '')
bot = telebot.TeleBot(token, threaded=False)

# Convertimos la variable de entorno a entero, con fallback a 0 si no existe
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

# ===== DECORADOR ADMIN =====

def admin_only(func):
    """Decorador que restringe el comando solo al admin."""
    @wraps(func)
    def wrapper(m):
        if m.chat.id != ADMIN_CHAT_ID:
            bot.reply_to(m, "⛔ Comando exclusivo del administrador.")
            return
        return func(m)
    return wrapper

# ===== HELPERS TELEBOT =====

def build_timezone_markup():
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    for row in timezone_keyboard_payload()["inline_keyboard"]:
        markup.row(*[InlineKeyboardButton(button["text"], callback_data=button["callback_data"]) for button in row])
    return markup

# ===== MANEJADORES DE COMANDOS =====

@bot.message_handler(commands=['start'])
def cmd_start(m):
    log_command(m.chat.id, '/start')
    bot.reply_to(m, start_response(add_user(m.chat.id)))

@bot.message_handler(commands=['help'])
def cmd_help(m):
    log_command(m.chat.id, '/help')
    bot.reply_to(m, help_text(is_admin=m.chat.id == ADMIN_CHAT_ID))

@bot.message_handler(commands=['subscribe'])
def cmd_subscribe(m):
    log_command(m.chat.id, '/subscribe')
    bot.reply_to(m, subscription_response(set_news_enabled(m.chat.id, True), enabled=True))

@bot.message_handler(commands=['unsubscribe'])
def cmd_unsubscribe(m):
    log_command(m.chat.id, '/unsubscribe')
    bot.reply_to(m, subscription_response(set_news_enabled(m.chat.id, False), enabled=False))

@bot.message_handler(commands=['prices'])
def cmd_prices(m):
    log_command(m.chat.id, '/prices')
    bot.send_message(m.chat.id, obtener_precios(), parse_mode='Markdown')

@bot.message_handler(commands=['mercados'])
def cmd_mercados(m):
    log_command(m.chat.id, '/mercados')
    bot.send_message(
        m.chat.id,
        markets_response(get_user_timezone(m.chat.id), obtener_estado_mercados),
        parse_mode='Markdown',
    )

@bot.message_handler(commands=['timezone'])
def cmd_timezone(m):
    log_command(m.chat.id, '/timezone')
    bot.send_message(
        m.chat.id,
        "🌍 **Configuración de Zona Horaria**\nSeleccioná tu región para que los horarios del mercado aparezcan en tu hora local:",
        reply_markup=build_timezone_markup(),
        parse_mode='Markdown',
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('tz|'))
def callback_timezone(call):
    tz_string = call.data.split('|')[1]
    response = timezone_callback_response(tz_string, set_user_timezone(call.message.chat.id, tz_string))
    bot.answer_callback_query(call.id, response["answer_text"], show_alert=response["show_alert"])
    if response["message_text"]:
        bot.edit_message_text(
            response["message_text"],
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown',
        )

@bot.message_handler(commands=['noticias'])
def cmd_noticias(m):
    log_command(m.chat.id, '/noticias')
    bot.send_chat_action(m.chat.id, 'typing')
    messages = news_messages(buscar_noticias())
    bot.reply_to(m, messages[0])
    for message in messages[1:]:
        bot.send_message(m.chat.id, message, parse_mode='Markdown')

# ===== COMANDOS DE ADMIN =====

@bot.message_handler(commands=['stats'])
@admin_only
def cmd_stats(m):
    log_command(m.chat.id, '/stats')
    bot.reply_to(m, stats_response(get_user_stats()))

@bot.message_handler(commands=['broadcast'])
@admin_only
def cmd_broadcast(m):
    log_command(m.chat.id, '/broadcast')
    text = extract_broadcast_text(
        m.text,
        reply_text=(m.reply_to_message.text if m.reply_to_message else None),
        reply_caption=(m.reply_to_message.caption if m.reply_to_message else None),
    )
    if not text:
        bot.reply_to(m, "❌ Usá: /broadcast <mensaje> o respondé a un mensaje con /broadcast")
        return

    users = get_all_users()
    if not users:
        bot.reply_to(m, "❌ No hay usuarios registrados.")
        return

    sent = 0
    failed = 0
    for uid in users:
        try:
            bot.send_message(uid, f"📢 **Mensaje del admin:**\n\n{text}", parse_mode='Markdown')
            sent += 1
        except Exception as e:
            print(f"Error broadcasting to {uid}: {e}")
            failed += 1

    bot.reply_to(m, f"✅ Broadcast enviado: {sent} exitosos, {failed} fallidos.")

@bot.message_handler(commands=['ban'])
@admin_only
def cmd_ban(m):
    log_command(m.chat.id, '/ban')
    target_id, error = ban_target(m.text)
    if error:
        bot.reply_to(m, error)
        return

    bot.reply_to(m, ban_response(ban_user(target_id), target_id))

# ===== HANDLER PARA VERCEL =====

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            # Pasar la actualización a telebot
            json_string = post_data.decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            print(f"Error procesando Webhook: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Error")
