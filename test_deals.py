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

    def test_focus_months_add_dated_searches(self):
        config = {
            "origins": {"MAA": 0},
            "trip_types": ["round_trip"],
            "return_airports": {},
            "regions": {"japan": {"destinations": {"TYO": "Tokyo"}, "focus_months": ["2027-02"]}},
        }
        found = [(s[0], s[-1]) for s in deals.searches(config)]
        self.assertEqual(found, [("MAA-TYO-round_trip", None), ("MAA-TYO-round_trip@2027-02", "2027-02")])


class LinksTest(unittest.TestCase):
    def test_one_way(self):
        t = {"origin": "SHA", "origin_airport": "PVG", "destination": "BLR",
             "departure_at": "2027-01-29T08:15:00+08:00"}
        (g_name, g), (s_name, s) = deals.compare_links(t)
        self.assertIn("Flights+from+PVG+to+BLR+on+2027-01-29+one+way", g)
        self.assertEqual(s, "https://www.skyscanner.co.in/transport/flights/pvg/blr/270129/")

    def test_round_trip(self):
        t = {"origin": "DEL", "destination": "GVA",
             "departure_at": "2027-04-02T01:00:00+05:30", "return_at": "2027-04-09T10:00:00+02:00"}
        (_, g), (_, s) = deals.compare_links(t)
        self.assertIn("returning+2027-04-09", g)
        self.assertTrue(s.endswith("/del/gva/270402/270409/"))


if __name__ == "__main__":
    unittest.main()
