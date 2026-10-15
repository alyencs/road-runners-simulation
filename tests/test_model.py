"""
Automated tests for the Road Runners simulation.

Run from the project folder with:   python -m unittest discover -s tests -v

Expected values are worked out by hand in the comments, so each test can be
checked without running the program.
"""

import contextlib
import csv
import io
import os
import random
import sys
import tempfile
import unittest
from unittest import mock

import matplotlib

matplotlib.use("Agg")  # tests never open windows

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from roadrunners import charts, interface  # noqa: E402
from roadrunners.model import (NO_FEEDBACK, FeedbackRules, classify_condition, classify_los,  # noqa: E402
                               simulate, waiting_in_hour)


class TestHandCalculatedCase(unittest.TestCase):
    """Arrival 1100 veh/h, capacity 1000 veh/h, 6 hours, no queue at the start."""

    def setUp(self):
        self.r = simulate(1100, 1000, 6)

    def test_hour_by_hour(self):
        # Ratio before hour 1 = 1100/1000 = 1.10 -> Building -> 5% reroute -> 1045 arrive.
        # Queue grows 45/h until hour 5 (ratio 1.225 > 1.20 = Severe); hour 6 then has
        # 10% rerouting (990 arrive) and 5% capacity loss (950 pass): +40.
        self.assertEqual(self.r.queue_line(), [0, 45, 90, 135, 180, 225, 265])
        self.assertEqual([round(h.demand_ratio, 3) for h in self.r.hourly],
                         [1.045, 1.09, 1.135, 1.18, 1.225, 1.279])
        self.assertEqual([h.condition for h in self.r.hourly], ["Building"] * 4 + ["Severe"] * 2)
        self.assertEqual(self.r.hourly[-1].arrivals, 990)
        self.assertEqual(self.r.hourly[-1].capacity, 950)

    def test_totals_and_delay(self):
        # Waiting areas: 22.5 + 67.5 + 112.5 + 157.5 + 202.5 + 245 = 807.5 vehicle-hours
        # Vehicles: 5 x 1045 + 990 = 6215 -> 807.5 / 6215 h = 7.80 min per vehicle
        self.assertAlmostEqual(self.r.total_arrived, 6215)
        self.assertAlmostEqual(self.r.total_served, 5950)
        self.assertAlmostEqual(self.r.total_rerouted, 5 * 55 + 110)
        self.assertAlmostEqual(self.r.total_capacity_lost, 50)
        self.assertAlmostEqual(sum(h.waiting for h in self.r.hourly), 807.5)
        self.assertAlmostEqual(self.r.average_delay_minutes, 807.5 / 6215 * 60)
        self.assertEqual(self.r.longest_queue, 265)
        self.assertEqual((self.r.worst_hour.condition, self.r.worst_hour.los), ("Severe", "F"))


class TestRules(unittest.TestCase):
    def test_los_boundaries(self):
        for ratio, letter in [(0, "A"), (0.35, "A"), (0.36, "B"), (0.54, "B"), (0.77, "C"),
                              (0.93, "D"), (0.94, "E"), (1.0, "E"), (1.0001, "F")]:
            self.assertEqual(classify_los(ratio), letter, ratio)

    def test_condition_boundaries(self):
        for ratio, cond in [(0.5, "Stable"), (1.0, "Stable"), (1.0001, "Building"),
                            (1.2, "Building"), (1.2001, "Severe")]:
            self.assertEqual(classify_condition(ratio), cond, ratio)

    def test_feedback_uses_previous_hour(self):
        r = simulate(1100, 1000, 12)
        shares = FeedbackRules().reroute_share
        for before, now in zip(r.hourly, r.hourly[1:]):
            expected = shares[("Stable", "Building", "Severe").index(before.condition)]
            self.assertAlmostEqual(now.rerouted, 1100 * expected)

    def test_feedback_direction(self):
        # Rerouting (balancing loop) lowers the queue; spillback (reinforcing loop) raises it.
        none = simulate(1100, 1000, 12, rules=NO_FEEDBACK).final_queue
        reroute_only = simulate(1100, 1000, 12, rules=FeedbackRules(capacity_loss=(0, 0, 0))).final_queue
        spill_only = simulate(1100, 1000, 12, rules=FeedbackRules(reroute_share=(0, 0, 0))).final_queue
        both = simulate(1100, 1000, 12).final_queue
        self.assertEqual((none, reroute_only, spill_only, both), (1200, 210, 1650, 505))


class TestStockAndFlow(unittest.TestCase):
    def test_no_feedback_closed_form(self):
        # Without feedback Queue(t) = (A - C) x t exactly.
        r = simulate(1200, 1000, 10, rules=NO_FEEDBACK)
        self.assertEqual(r.queue_line(), [200 * t for t in range(11)])

    def test_below_capacity_never_queues(self):
        r = simulate(999.9, 1000, 48)
        self.assertTrue(all(h.queue == 0 and h.served == h.arrivals for h in r.hourly))
        self.assertEqual(r.average_delay_minutes, 0)

    def test_starting_queue_drains(self):
        # 2500 waiting, no arrivals, no feedback: 1500, 500, 0, 0
        # Waiting: (2500+1500)/2 + (1500+500)/2 + 500*0.5/2 = 2000 + 1000 + 125 = 3125 veh-h
        r = simulate(0, 1000, 4, start_queue=2500, rules=NO_FEEDBACK)
        self.assertEqual(r.queue_line(), [2500, 1500, 500, 0, 0])
        self.assertAlmostEqual(r.average_delay_minutes, 3125 / 2500 * 60)

    def test_waiting_area_shapes(self):
        self.assertAlmostEqual(waiting_in_hour(0, 1100, 1000), 50)     # grows 0 -> 100
        self.assertAlmostEqual(waiting_in_hour(100, 900, 1000), 50)    # 100 -> 0 exactly at the end
        self.assertAlmostEqual(waiting_in_hour(50, 900, 1000), 12.5)   # empties after half an hour
        self.assertAlmostEqual(waiting_in_hour(0, 500, 1000), 0)

    def test_physical_rules_on_random_inputs(self):
        rng = random.Random(7)
        for _ in range(500):
            a, c = rng.uniform(0, 5000), rng.uniform(1, 4000)
            q0, hours = rng.choice([0, rng.randint(0, 20000)]), rng.randint(1, 60)
            r = simulate(a, c, hours, q0)
            for h in r.hourly:
                self.assertGreaterEqual(h.queue, 0)
                self.assertGreaterEqual(h.waiting, 0)
                self.assertLessEqual(h.served, h.capacity + 1e-6)          # cannot exceed capacity
                self.assertLessEqual(h.arrivals, a + 1e-9)                   # rerouting never adds cars
            line = r.queue_line()
            for h, before in zip(r.hourly, line):
                self.assertLessEqual(h.served, before + h.arrivals + 1e-6)  # cannot serve absent cars
            self.assertLess(abs(r.balance_error), 1e-6)                      # no vehicle lost or created

    def test_more_arrivals_or_less_capacity_means_longer_queue(self):
        queues = [simulate(a, 1000, 6).final_queue for a in range(500, 1501, 50)]
        self.assertEqual(queues, sorted(queues))
        self.assertEqual(queues[:11], [0] * 11)       # up to arrival = capacity: no queue
        queues = [simulate(1100, c, 6).final_queue for c in range(600, 1501, 50)]
        self.assertEqual(queues, sorted(queues, reverse=True))

    def test_invalid_model_inputs_rejected(self):
        for args in [(-1, 1000, 5), (100, 0, 5), (100, 1000, 0), (100, 1000, 5, -3)]:
            with self.assertRaises(ValueError):
                simulate(*args)


class TestQueueVerdict(unittest.TestCase):
    def test_each_outcome(self):
        self.assertEqual(simulate(750, 800, 6).queue_trend()[0], "NO QUEUE")
        self.assertEqual(simulate(1100, 1000, 6).queue_trend()[0], "QUEUE GROWING")
        self.assertEqual(simulate(800, 1000, 6, start_queue=500).queue_trend()[0], "QUEUE CLEARED")
        self.assertEqual(simulate(800, 1000, 2, start_queue=5000).queue_trend()[0], "QUEUE SHRINKING")
        self.assertEqual(simulate(1040, 1000, 12).queue_trend()[0], "BUILDS UP AND CLEARS REPEATEDLY")
        self.assertEqual(simulate(1000, 1000, 6, start_queue=100, rules=NO_FEEDBACK).queue_trend()[0],
                         "QUEUE STABLE")

    def test_cleared_hour_is_correct(self):
        # 500 waiting, 800 arrive (Severe first: 720 arrive, 950 pass) -> 270, 40, 0
        r = simulate(800, 1000, 6, start_queue=500)
        self.assertEqual(r.queue_line()[:4], [500, 270, 40, 0])
        self.assertIn("end of hour 3", r.queue_trend()[1])


class TestInputChecking(unittest.TestCase):
    def check(self, key, text):
        return interface.parse_value(interface.BY_KEY[key], text)

    def test_valid_custom_values_are_accepted(self):
        self.assertEqual(self.check("1", "5000"), (5000.0, None))
        self.assertEqual(self.check("1", "0"), (0.0, None))
        self.assertEqual(self.check("1", "1,250.5"), (1250.5, None))
        self.assertEqual(self.check("2", "0.5"), (0.5, None))
        self.assertEqual(self.check("3", "1"), (1, None))
        self.assertEqual(self.check("3", "720"), (720, None))
        self.assertEqual(self.check("3", "24.0"), (24, None))
        self.assertEqual(self.check("4", " 300 "), (300, None))

    def test_invalid_values_are_rejected_with_plain_messages(self):
        cases = {"1": ["-5", "abc", "", "nan", "inf", "1000001"],
                 "2": ["0", "-1", "ten"],
                 "3": ["0", "721", "2.5", "-3"],
                 "4": ["-1", "2.5", "x"]}
        for key, texts in cases.items():
            for text in texts:
                value, error = self.check(key, text)
                self.assertIsNone(value, (key, text))
                self.assertTrue(error.startswith("Please enter"), (key, text, error))

    def test_custom_values_reach_the_model(self):
        # Results must change with the user's own numbers, not stay at the examples.
        for a, c in [(5000, 4000), (300, 1000), (2500, 2499), (0, 10)]:
            r = simulate(a, c, 10)
            self.assertEqual((r.arrival_rate, r.road_capacity), (a, c))
            no_feedback_growth = max(0.0, a - c) * 10
            self.assertLessEqual(r.final_queue, no_feedback_growth + 1e-6 if a > c else 0)


class TestProgram(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_program(self, answers):
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(out):
            code = interface.main(results_dir=self.tmp.name, show_chart=False)
        return code, out.getvalue()

    def test_full_demonstration_session(self):
        code, text = self.run_program([
            "x",            # unknown choice
            "t",            # table before any run -> not offered yet
            "r",            # run with the example values
            "1", "-5", "abc", "1200",   # change arrival: two bad entries, then 1200
            "2", "",        # open capacity, press Enter -> keep 1000
            "R",            # second run, compared with the first
            "T", "H", "Q"])
        self.assertEqual(code, 0)
        self.assertNotIn("Traceback", text)
        self.assertIn("Please type R, 1, 2, 3, 4, H or Q", text)
        self.assertIn("Please enter a number of 0 or more for the vehicle arrival rate", text)
        self.assertIn("Kept 1,000 vehicles/hour", text)
        self.assertIn("changed from 1,100 to 1,200", text)
        self.assertIn("Previous run", text)
        self.assertIn("HOUR-BY-HOUR RESULTS", text)
        self.assertIn("HOW THE MODEL WORKS", text)
        self.assertIn("balanced: no vehicles lost or created", text)
        self.assertTrue(text.rstrip().endswith("Goodbye."))
        self.assertEqual(len([f for f in os.listdir(self.tmp.name) if f.endswith(".png")]), 2)

    def test_end_of_input_exits_cleanly(self):
        code, text = self.run_program(["R", EOFError()])  # input stream closes after one run
        self.assertEqual(code, 0)
        self.assertIn("Goodbye.", text)

    def test_saved_table_and_chart_match_the_simulation(self):
        self.run_program(["4", "500", "1", "900", "R", "Q"])
        r = simulate(900, 1000, 12, start_queue=500)
        csv_file = [f for f in os.listdir(self.tmp.name) if f.endswith(".csv")][0]
        with open(os.path.join(self.tmp.name, csv_file), encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([float(row["queue_at_end"]) for row in rows], [h.queue for h in r.hourly])
        self.assertEqual([float(row["vehicles_passed"]) for row in rows], [h.served for h in r.hourly])

        fig = charts.draw(r)
        queue_line = [ln for ln in fig.axes[0].get_lines() if ln.get_label() == "This run"][0]
        self.assertEqual(list(queue_line.get_ydata()), r.queue_line())
        matplotlib.pyplot.close(fig)


if __name__ == "__main__":
    unittest.main()
