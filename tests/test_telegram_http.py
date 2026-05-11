import json
import unittest

import httpx

from bot.telegram_http import TelegramHttpClient


class TelegramHttpClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_message_posts_to_telegram_api(self):
        requests = []

        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 123}})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        telegram = TelegramHttpClient("token-123", client=client, base_url="https://telegram.test")

        result = await telegram.send_message(42, "hello")

        self.assertTrue(result["ok"])
        self.assertEqual(str(requests[0].url), "https://telegram.test/bottoken-123/sendMessage")
        self.assertEqual(requests[0].method, "POST")
        self.assertEqual(json.loads(requests[0].read()), {"chat_id": 42, "text": "hello", "parse_mode": "Markdown"})
        await client.aclose()

    async def test_send_message_raises_when_telegram_returns_not_ok(self):
        async def handler(request):
            return httpx.Response(200, json={"ok": False, "description": "chat not found"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        telegram = TelegramHttpClient("token-123", client=client, base_url="https://telegram.test")

        with self.assertRaisesRegex(RuntimeError, "chat not found"):
            await telegram.send_message(42, "hello")

        await client.aclose()

    async def test_send_message_requires_token(self):
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
        telegram = TelegramHttpClient("", client=client)

        with self.assertRaisesRegex(ValueError, "TELEGRAM_TOKEN"):
            await telegram.send_message(42, "hello")

        await client.aclose()


if __name__ == "__main__":
    unittest.main()
