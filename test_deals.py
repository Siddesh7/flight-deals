import unittest

import deals

CONFIG = {"min_history": 3, "relative_drop": 0.35}


class EvaluateTest(unittest.TestCase):
    def test_under_absolute_limit(self):
        self.assertTrue(deals.evaluate(39000, [], 40000, CONFIG))

    def test_normal_price_is_not_a_deal(self):
        self.assertEqual(deals.evaluate(52000, [50000, 55000, 53000], 40000, CONFIG), [])

    def test_big_drop_vs_usual(self):
        reasons = deals.evaluate(60000, [100000, 95000, 105000], 40000, CONFIG)
        self.assertEqual(len(reasons), 1)
        self.assertIn("40% below usual", reasons[0])

    def test_needs_enough_history(self):
        self.assertEqual(deals.evaluate(60000, [100000, 100000], 40000, CONFIG), [])


class SearchesTest(unittest.TestCase):
    def test_one_way_back_flips_direction(self):
        config = {
            "origins": {"MAA": 0},
            "trip_types": ["round_trip", "one_way_back"],
            "return_airports": {"MAA": 0, "DEL": 6000},
            "regions": {"europe": {"destinations": {"AMS": "Amsterdam"}}},
        }
        keys = [s[0] for s in deals.searches(config)]
        self.assertEqual(keys, ["MAA-AMS-round_trip", "AMS-MAA-one_way_back", "AMS-DEL-one_way_back"])


if __name__ == "__main__":
    unittest.main()
