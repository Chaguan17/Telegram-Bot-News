import asyncio
import unittest
from types import SimpleNamespace

from bot.news_service import (
    buscar_noticias_with_async_loader,
    buscar_noticias_with_loader,
    filter_news_entries,
    hash_string,
)


class NewsServiceTests(unittest.TestCase):
    def test_filter_news_entries_scores_and_limits_high_impact_news(self):
        feeds = [
            (
                "https://example.com/feed",
                [
                    {"title": "Fed confirma inflación y tasas", "link": "https://a.test"},
                    {"title": "Deportes sin impacto", "link": "https://b.test"},
                ],
            ),
            (
                "https://es.beincrypto.com/feed/",
                [SimpleNamespace(title="Resumen cripto menor", link="https://c.test")],
            ),
        ]

        result = filter_news_entries(feeds)

        self.assertEqual(len(result), 1)  # Solo la primera tiene score >= 4
        expected_hash = hash_string("Fed confirma inflación y tasas" + "https://a.test")
        self.assertEqual(result[0]["hash"], expected_hash)
        self.assertIn("🔴 IMPACTO", result[0]["message"])
        self.assertIn("https://a.test", result[0]["message"])

    def test_buscar_noticias_with_loader_skips_failed_feed(self):
        def loader(url):
            if "bad" in url:
                raise RuntimeError("feed down")
            return [{"title": "Breaking ataque mercado", "link": "https://ok.test"}]

        result = buscar_noticias_with_loader(loader, feeds=["https://bad.test", "https://ok.test"])

        self.assertEqual(len(result), 1)
        self.assertIn("Breaking ataque mercado", result[0]["message"])

    def test_buscar_noticias_with_async_loader_skips_failed_feed(self):
        async def loader(url):
            if "bad" in url:
                raise RuntimeError("feed down")
            return [{"title": "Breaking ataque mercado", "link": "https://ok.test"}]

        result = asyncio.run(buscar_noticias_with_async_loader(
            loader,
            feeds=["https://bad.test", "https://ok.test"],
        ))

        self.assertEqual(len(result), 1)
        self.assertIn("Breaking ataque mercado", result[0]["message"])


if __name__ == "__main__":
    unittest.main()
