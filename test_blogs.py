import json
import unittest

import blogs
from deals import CONFIG

WORDS = blogs.keywords(json.loads(CONFIG.read_text()))


class MatchTest(unittest.TestCase):
    def test_india_destination(self):
        self.assertTrue(blogs.matches("Cheap Flights: New York to Delhi, India $689 round-trip", WORDS))

    def test_india_origin(self):
        self.assertTrue(blogs.matches("Cheap Flights (ONE-WAY): Mumbai to Chicago $310", WORDS))

    def test_skips_us_to_europe(self):
        self.assertFalse(blogs.matches("Cheap Flights: New York to Milan $514-$550 round-trip – Condor", WORDS))

    def test_skips_us_to_asia(self):
        self.assertFalse(blogs.matches(
            "Nonstop Flights (ONE-WAY): Los Angeles to Singapore $313-$377 [Jan-Mar]", WORDS))

    def test_skips_domestic(self):
        self.assertFalse(blogs.matches(
            "Nonstop Flights: Atlanta to/from Orlando, Tampa $84 round-trip – Southwest", WORDS))


class PriceTest(unittest.TestCase):
    BLOGS = {"max_price_inr": 50000, "fx_to_inr": {"$": 88, "€": 95, "£": 112}}

    def test_parses_first_price(self):
        self.assertEqual(blogs.price_inr("Boston - New Delhi. $806 (Basic) / $956", self.BLOGS["fx_to_inr"]), 806 * 88)

    def test_skips_expensive(self):
        self.assertFalse(blogs.cheap_enough("Qatar Airways: Philadelphia – Chennai, India. $842. Roundtrip", self.BLOGS))

    def test_keeps_cheap_and_unpriced(self):
        self.assertTrue(blogs.cheap_enough("Flights from Frankfurt to Delhi from €299", self.BLOGS))
        self.assertTrue(blogs.cheap_enough("Error fare to Mumbai!", self.BLOGS))


class RssTest(unittest.TestCase):
    def test_parse_rss(self):
        xml = b"""<?xml version="1.0"?><rss><channel>
<item><title>Flights from Frankfurt to Delhi, India from &#8364;299</title>
<link>https://example.com/a</link><guid>https://example.com/?p=1</guid>
<pubDate>Wed, 25 Nov 2026 14:50:59 +0000</pubDate></item>
</channel></rss>"""
        [post] = blogs.parse_rss(xml)
        self.assertEqual(post["id"], "https://example.com/?p=1")
        self.assertEqual(post["title"], "Flights from Frankfurt to Delhi, India from \u20ac299")
        self.assertEqual(post["posted"].isoformat(), "2026-11-25T14:50:59+00:00")
        self.assertTrue(blogs.matches(post["title"], WORDS))


if __name__ == "__main__":
    unittest.main()
