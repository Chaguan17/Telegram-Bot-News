import unittest

from cloudflare.rss import parse_rss_entries


class CloudflareRssTests(unittest.TestCase):
    def test_parse_rss_entries(self):
        entries = parse_rss_entries("""
        <rss><channel><item>
          <title>Breaking BTC news</title>
          <link>https://example.com/news</link>
        </item></channel></rss>
        """)

        self.assertEqual(entries, [{"title": "Breaking BTC news", "link": "https://example.com/news"}])

    def test_parse_atom_entries(self):
        entries = parse_rss_entries("""
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Atom BTC news</title>
            <link href="https://example.com/atom" />
          </entry>
        </feed>
        """)

        self.assertEqual(entries, [{"title": "Atom BTC news", "link": "https://example.com/atom"}])


if __name__ == "__main__":
    unittest.main()
