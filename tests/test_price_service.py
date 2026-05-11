import unittest

from bot.price_service import format_prices, obtener_precios_with_async_loader


class PriceServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_format_prices(self):
        self.assertIn(
            "BTC",
            format_prices([
                {"symbol": "BTCUSDT", "price": "100000"},
                {"symbol": "ETHUSDT", "price": "3000"},
                {"symbol": "BNBUSDT", "price": "600"},
            ]),
        )

    async def test_async_loader_returns_fallback_on_error(self):
        async def loader(symbols):
            raise RuntimeError("binance down")

        self.assertIn("Error", await obtener_precios_with_async_loader(loader))


if __name__ == "__main__":
    unittest.main()
