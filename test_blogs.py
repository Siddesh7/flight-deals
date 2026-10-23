import unittest

import blogs

WORDS = {"singapore", "milan", "costa rica", "delhi"}


class MatchTest(unittest.TestCase):
    def test_destination_part(self):
        self.assertEqual(
            blogs.destination_part("Nonstop Flights (ONE-WAY): Los Angeles to Singapore $313-$377 [Jan-Mar]"),
            "Singapore")
        self.assertEqual(
            blogs.destination_part("Nonstop Flights: Newark/New York to Liberia, Costa Rica $272 round-trip"),
            "Liberia, Costa Rica")

    def test_matches_international(self):
        self.assertTrue(blogs.matches("Cheap Flights: New York to Milan $514-$550 round-trip – Condor", WORDS))

    def test_skips_domestic(self):
        self.assertFalse(blogs.matches(
            "Nonstop Flights: Atlanta to/from Orlando, Tampa $84 round-trip – Southwest", WORDS))

    def test_origin_does_not_count(self):
        # A Singapore origin shouldn't match; only the destination should.
        self.assertFalse(blogs.matches("Cheap Flights: Singapore to Orlando $500 round-trip", WORDS))


if __name__ == "__main__":
    unittest.main()
