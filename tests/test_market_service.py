import unittest

from bot.market_service import obtener_estado_mercados, timezone_or_default


class MarketServiceTests(unittest.TestCase):
    def test_timezone_or_default_uses_zoneinfo(self):
        self.assertIn("America/Caracas", str(timezone_or_default("America/Caracas")))
        self.assertIn("Europe/Madrid", str(timezone_or_default("bad/timezone")))

    def test_obtener_estado_mercados_returns_market_message(self):
        message = obtener_estado_mercados(timezone_or_default("America/Caracas"))

        self.assertIn("MERCADOS", message)
        self.assertIn("Asia", message)
        self.assertIn("Europa", message)
        self.assertIn("EE.UU.", message)


if __name__ == "__main__":
    unittest.main()
