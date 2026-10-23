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


if __name__ == "__main__":
    unittest.main()
