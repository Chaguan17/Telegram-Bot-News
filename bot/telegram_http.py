import httpx


class TelegramHttpClient:
    """Async Telegram Bot API client for Worker-friendly runtimes."""

    def __init__(self, token: str, *, client=None, base_url: str = "https://api.telegram.org"):
        self.token = token
        self.client = client or httpx.AsyncClient(timeout=10)
        self.base_url = base_url.rstrip("/")

    async def _post(self, method: str, payload: dict) -> dict:
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN is required")

        response = await self.client.post(
            f"{self.base_url}/bot{self.token}/{method}",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok", False):
            description = data.get("description", "Telegram API returned ok=false")
            raise RuntimeError(description)
        return data

    async def send_message(self, chat_id: int, message: str, *, parse_mode: str = "Markdown", reply_markup=None) -> dict:
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._post("sendMessage", payload)

    async def answer_callback_query(self, callback_query_id: str, text: str, *, show_alert: bool = False) -> dict:
        return await self._post("answerCallbackQuery", {
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": show_alert,
        })

    async def edit_message_text(self, chat_id: int, message_id: int, text: str, *, parse_mode: str = "Markdown") -> dict:
        return await self._post("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        })
