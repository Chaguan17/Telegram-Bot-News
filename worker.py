import json
from urllib.parse import urlparse
import js
from pyodide.ffi import to_js
from workers import Response, WorkerEntrypoint

from bot.cron_service import run_news_cron_async
from bot.market_service import obtener_estado_mercados
from bot.news_service import RSS_FEEDS, buscar_noticias_with_async_loader
from bot.price_service import obtener_precios_with_async_loader
from bot.repositories.d1_binding_repository import D1BindingRepository
from bot.webhook_service import handle_telegram_update
from bot.dashboard_html import DASHBOARD_HTML
from bot.utils.rss_parser import parse_rss_custom


class CloudflareTelegramClient:
    def __init__(self, token: str):
        self.token = token

    async def _post(self, method: str, payload: dict):
        if not self.token:
            raise RuntimeError("TELEGRAM_TOKEN is not configured")

        response = await js.fetch(
            f"https://api.telegram.org/bot{self.token}/{method}",
            to_js({
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload),
            }),
        )
        if not response.ok:
            raise RuntimeError(f"Telegram API HTTP {response.status}")
        data = (await response.json()).to_py()
        if not data.get("ok", False):
            raise RuntimeError(f"Telegram API error: {data}")
        return data

    async def send_message(self, chat_id, message, parse_mode="Markdown", reply_markup=None):
        payload = {"chat_id": chat_id, "text": message, "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self._post("sendMessage", payload)

    async def answer_callback_query(self, callback_query_id, text, show_alert=False):
        return await self._post(
            "answerCallbackQuery",
            {"callback_query_id": callback_query_id, "text": text, "show_alert": show_alert},
        )

    async def edit_message_text(self, chat_id, message_id, text, parse_mode="Markdown"):
        return await self._post(
            "editMessageText",
            {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode},
        )


async def fetch_feed_entries(url: str):
    try:
        response = await js.fetch(url, to_js({
            "method": "GET",
            "headers": {"User-Agent": "Mozilla/5.0"},
            "cache": "no-store"
        }))
        if response.status != 200:
            print(f"Error fetching feed {url}: Status {response.status}")
            return []
        text = await response.text()
        return parse_rss_custom(text)
    except Exception as e:
        print(f"Exception fetching feed {url}: {e}")
        return []


async def fetch_binance_prices(symbols: list[str]):
    import json
    from urllib.parse import quote
    symbols_str = quote(json.dumps(symbols, separators=(',', ':')))
    url = f"https://api.binance.com/api/v3/ticker/price?symbols={symbols_str}"
    
    response = await js.fetch(url, to_js({
        "method": "GET",
        "headers": {"User-Agent": "Mozilla/5.0"}
    }))
    
    if response.status != 200:
        status_text = await response.text()
        raise RuntimeError(f"Binance status {response.status}: {status_text}")
    
    data_text = await response.text()
    return json.loads(data_text)


def json_response(payload, *, status: int = 200):
    return Response.json(
        payload,
        status=status,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json",
        },
    )


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        pathname = urlparse(request.url).path
        repository = D1BindingRepository(self.env.DB)

        if pathname == "/":
            return Response(DASHBOARD_HTML, headers={"Content-Type": "text/html"})

        if pathname == "/api/stats":
            return json_response(await repository.get_dashboard_stats())

        if pathname == "/api/debug-cron":
            print("[DEBUG] Disparo manual de Cron solicitado via URL")
            await self.scheduled(None, None, None)
            return json_response({"status": "debug_cron_triggered", "msg": "Revisa los logs."})

        if pathname == "/api/webhook":
            if request.method != "POST":
                return json_response({"error": "Method not allowed"}, status=405)
            telegram = CloudflareTelegramClient(self.env.TELEGRAM_TOKEN)
            admin_chat_id = int(getattr(self.env, "ADMIN_CHAT_ID", "0") or "0")
            result = await handle_telegram_update(
                await request.json(),
                repository=repository,
                telegram=telegram,
                admin_chat_id=admin_chat_id,
                get_prices=lambda: obtener_precios_with_async_loader(fetch_binance_prices),
                get_market_state=obtener_estado_mercados,
                get_news=lambda: buscar_noticias_with_async_loader(fetch_feed_entries, feeds=RSS_FEEDS),
            )
            return json_response(result)

        return json_response({"error": "Not found"}, status=404)

    async def scheduled(self, event, env, ctx):
        repository = D1BindingRepository(self.env.DB)
        telegram = CloudflareTelegramClient(self.env.TELEGRAM_TOKEN)

        result = await run_news_cron_async(
            buscar_noticias=lambda: buscar_noticias_with_async_loader(fetch_feed_entries, feeds=RSS_FEEDS),
            get_news_subscribers=repository.get_news_subscribers,
            is_news_sent=repository.is_news_sent,
            mark_news_sent=repository.mark_news_sent,
            send_message=telegram.send_message,
            update_bot_health=repository.update_bot_health,
        )
        print(f"cron processed: {result}")
