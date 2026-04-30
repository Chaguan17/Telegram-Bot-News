import os
import sys
from functools import wraps
from http.server import BaseHTTPRequestHandler
import telebot

# Añadir el root del proyecto al path para importar bot.services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.services import obtener_precios, obtener_estado_mercados, buscar_noticias
from bot.db import add_user, set_news_enabled, get_user_stats, ban_user, get_all_users, log_command

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

# ===== MANEJADORES DE COMANDOS =====

@bot.message_handler(commands=['start'])
def cmd_start(m):
    log_command(m.chat.id, '/start')
    result = add_user(m.chat.id)
    status = result.get("status")
    news_on = result.get("news_enabled", True)
    if status == "new":
        bot.reply_to(m, "🚀 **Bot Serverless Activo**\n• Suscrito a noticias automáticas.\n• /help : Ver comandos disponibles")
    elif status == "existing":
        state = "**activadas**" if news_on else "**desactivadas**"
        toggle = "/unsubscribe para desactivar" if news_on else "/subscribe para reactivar"
        bot.reply_to(m, f"🤖 **Ya estás registrado.** Las noticias automáticas están {state}. Usá {toggle} o /help para ver comandos.")
    else:
        bot.reply_to(m, "❌ Error de conexión con la base de datos. Intentá más tarde.")

@bot.message_handler(commands=['help'])
def cmd_help(m):
    log_command(m.chat.id, '/help')
    text = ("📋 **Comandos disponibles:**\n\n"
            "• /start — Suscribirse al bot\n"
            "• /subscribe — Activar noticias automáticas\n"
            "• /unsubscribe — Desactivar noticias automáticas\n"
            "• /prices — Precios de BTC, ETH y BNB\n"
            "• /mercados — Estado de bolsas mundiales\n"
            "• /noticias — Top 3 noticias de impacto")
    if m.chat.id == ADMIN_CHAT_ID:
        text += ("\n\n👑 **Comandos de admin:**\n"
                 "• /stats — Estadísticas de usuarios\n"
                 "• /broadcast <mensaje> — Enviar mensaje a todos los suscritos\n"
                 "• /ban <chat_id> — Eliminar un usuario")
    bot.reply_to(m, text)

@bot.message_handler(commands=['subscribe'])
def cmd_subscribe(m):
    log_command(m.chat.id, '/subscribe')
    result = set_news_enabled(m.chat.id, True)
    if result == "ok":
        bot.reply_to(m, "✅ Noticias automáticas **activadas**. Recibirás noticias cada 15 min. Usá /unsubscribe para desactivar.")
    else:
        bot.reply_to(m, "❌ Primero debés usar /start para registrarte, o hay un error de conexión.")

@bot.message_handler(commands=['unsubscribe'])
def cmd_unsubscribe(m):
    log_command(m.chat.id, '/unsubscribe')
    result = set_news_enabled(m.chat.id, False)
    if result == "ok":
        bot.reply_to(m, "🔇 Noticias automáticas **desactivadas**. Seguís pudiendo usar /noticias para consultar a demanda. Usá /subscribe para reactivar.")
    else:
        bot.reply_to(m, "❌ Primero debés usar /start para registrarte, o hay un error de conexión.")

@bot.message_handler(commands=['prices'])
def cmd_prices(m):
    log_command(m.chat.id, '/prices')
    bot.send_message(m.chat.id, obtener_precios(), parse_mode='Markdown')

@bot.message_handler(commands=['mercados'])
def cmd_mercados(m):
    log_command(m.chat.id, '/mercados')
    bot.send_message(m.chat.id, obtener_estado_mercados(), parse_mode='Markdown')

@bot.message_handler(commands=['noticias'])
def cmd_noticias(m):
    log_command(m.chat.id, '/noticias')
    bot.send_chat_action(m.chat.id, 'typing')
    noticias = buscar_noticias()
    if not noticias:
        bot.reply_to(m, "No he encontrado noticias de alto impacto en los feeds en este momento.")
    else:
        bot.reply_to(m, "📰 **Top 3 Noticias de Impacto Actuales:**")
        for n in noticias:
            bot.send_message(m.chat.id, n['message'], parse_mode='Markdown')

# ===== COMANDOS DE ADMIN =====

@bot.message_handler(commands=['stats'])
@admin_only
def cmd_stats(m):
    log_command(m.chat.id, '/stats')
    stats = get_user_stats()
    bot.reply_to(m, f"📊 **Estadísticas de usuarios:**\n\n"
                     f"• Total registrados: {stats['total']}\n"
                     f"• Suscritos a noticias: {stats['subscribed']}\n"
                     f"• Desuscritos: {stats['unsubscribed']}")

@bot.message_handler(commands=['broadcast'])
@admin_only
def cmd_broadcast(m):
    log_command(m.chat.id, '/broadcast')
    # Extraer el mensaje después de /broadcast
    text = m.text.replace('/broadcast', '', 1).strip()
    
    # Si no hay texto, intentar sacar el texto del mensaje original (reply)
    if not text and m.reply_to_message:
        text = m.reply_to_message.text or m.reply_to_message.caption or ""
        # Limpiar separador si viene de GitHub Actions
        if "\n---\n⚠️ *Para enviar a todos" in text:
            text = text.split("\n---\n⚠️ *Para enviar a todos")[0].strip()
            
    if not text:
        bot.reply_to(m, "❌ Usá: /broadcast <mensaje> o respondé a un mensaje con /broadcast")
        return
    
    # Enviar a TODOS los usuarios registrados (suscritos y no suscritos)
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
    # Extraer el chat_id después de /ban
    parts = m.text.split()
    if len(parts) != 2:
        bot.reply_to(m, "❌ Usá: /ban <chat_id>")
        return
    
    try:
        target_id = int(parts[1])
    except ValueError:
        bot.reply_to(m, "❌ El chat_id debe ser un número.")
        return
    
    result = ban_user(target_id)
    if result == "deleted":
        bot.reply_to(m, f"✅ Usuario {target_id} eliminado.")
    elif result == "not_found":
        bot.reply_to(m, f"⚠️ Usuario {target_id} no encontrado.")
    else:
        bot.reply_to(m, "❌ Error de conexión con la base de datos.")

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