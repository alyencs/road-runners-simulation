"""
Tests for the web app helpers (roadrunners/web.py): input checking, tables and charts.

Run from the project folder with:   python -m unittest discover -s tests -v
"""

import csv
import io
import os
import sys
import unittest

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from roadrunners import web
except ImportError:  # altair/pandas not installed: only the terminal program's tests can run
    web = None

from roadrunners.interface import STARTING_VALUES  # noqa: E402
from roadrunners.model import simulate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chart_rows(chart):
    """All data rows of an Altair chart, as the browser receives them."""
    rows = []
    for values in chart.to_dict()["datasets"].values():
        rows.extend(values)
    return rows


@unittest.skipIf(web is None, "web app libraries are not installed (pip install -r requirements.txt)")
class TestInputs(unittest.TestCase):
    def test_starting_values_are_valid(self):
        values, errors = web.validate_inputs(STARTING_VALUES)
        self.assertEqual(errors, [])
        self.assertEqual(values, {"arrival_rate": 1100.0, "road_capacity": 1000.0, "hours": 12, "start_queue": 0})

    def test_other_valid_combinations(self):
        for raw in [{"arrival_rate": 0, "road_capacity": 0.5, "hours": 1, "start_queue": 0},
                    {"arrival_rate": 1_000_000, "road_capacity": 1_000_000, "hours": 720,
                     "start_queue": 10_000_000}]:
            values, errors = web.validate_inputs(raw)
            self.assertEqual(errors, [], raw)
            self.assertIsInstance(values["hours"], int)

    def test_invalid_values_give_the_programs_messages(self):
        raw = {"arrival_rate": -1, "road_capacity": 0, "hours": 2.5, "start_queue": None}
        values, errors = web.validate_inputs(raw)
        self.assertEqual(values, {})
        self.assertEqual(errors, [s.error for s in web.INPUTS.values()])

    def test_too_large(self):
        _, errors = web.validate_inputs(dict(STARTING_VALUES, hours=721))
        self.assertEqual(errors, ["Please enter 720 or less for the simulation duration "
                                  "(larger values are far beyond a single road)."])

    def test_run_uses_the_model(self):
        values, _ = web.validate_inputs({"arrival_rate": 1200, "road_capacity": 1000, "hours": 12,
                                         "start_queue": 0})
        self.assertEqual(web.run(values).queue_line(), simulate(1200, 1000, 12).queue_line())


@unittest.skipIf(web is None, "web app libraries are not installed")
class TestTables(unittest.TestCase):
    def setUp(self):
        self.r = simulate(1100, 1000, 12)

    def test_hourly_frame_is_the_model_output(self):
        frame = web.hourly_frame(self.r)
        self.assertEqual(len(frame), 12)
        self.assertEqual(list(frame["Queue at end of hour (veh)"]), [h.queue for h in self.r.hourly])
        self.assertEqual(list(frame["Vehicles passed (veh)"]), [h.served for h in self.r.hourly])
        self.assertEqual(list(frame["Traffic condition"]), [h.condition for h in self.r.hourly])
        self.assertEqual(list(frame["Level of Service"]), [h.los for h in self.r.hourly])

    def test_csv_download(self):
        rows = list(csv.DictReader(io.StringIO(web.csv_text(self.r))))
        self.assertEqual([float(row["queue_at_end"]) for row in rows], [h.queue for h in self.r.hourly])
        self.assertEqual([float(row["vehicles_arrived"]) for row in rows], [h.arrivals for h in self.r.hourly])

    def test_metric_cards(self):
        cards = {c["label"]: c for c in web.metric_cards(self.r)}
        self.assertEqual(cards["Vehicles arriving"]["value"], "12,155 veh")
        self.assertEqual(cards["Vehicles passing through"]["value"], "11,650 veh")
        self.assertEqual(cards["Vehicles still waiting"]["value"], "505 veh")
        self.assertEqual(cards["Longest queue"]["value"], "505 veh")
        self.assertEqual(cards["Average waiting time"]["value"], "15.4 min")
        self.assertEqual(cards["Worst traffic condition"]["value"], "Severe (LOS F)")
        self.assertTrue(all(c["delta"] is None for c in cards.values()))

    def test_metric_deltas_against_previous_run(self):
        cards = {c["label"]: c for c in web.metric_cards(simulate(1100, 1200, 12), self.r)}
        self.assertEqual(cards["Vehicles still waiting"]["delta"], "-505")
        self.assertEqual(cards["Average waiting time"]["delta"], "-15.4 min")
        self.assertEqual(cards["Vehicles still waiting"]["delta_color"], "inverse")
        unchanged = {c["label"]: c for c in web.metric_cards(self.r, self.r)}
        self.assertIsNone(unchanged["Longest queue"]["delta"])

    def test_comparison_frame(self):
        frame = web.comparison_frame(simulate(1200, 1000, 12), self.r, run_no=2)
        row = frame[frame["Measure"] == "Vehicles still waiting at the end"].iloc[0]
        self.assertEqual((row["This run (run 2)"], row["Previous run (run 1)"]), ("1,580", "505"))
        self.assertEqual(set(frame[""]), {"Settings", "What happened", "Feedback effects"})

    def test_rules_tables_follow_the_model(self):
        rules = web.rules_frame()
        self.assertEqual(list(rules["Drivers who reroute next hour"]), ["0%", "5%", "10%"])
        self.assertEqual(list(rules["Spillback: capacity lost next hour"]), ["0%", "0%", "5%"])
        self.assertEqual(list(web.los_frame()["Level of Service"]), list("ABCDEF"))

    def test_model_md_has_the_sections_the_app_shows(self):
        with open(os.path.join(ROOT, "MODEL.md"), encoding="utf-8") as handle:
            sections = web.doc_sections(handle.read())
        for heading in ["Structure", "Inputs (chosen by the user)", "Equations (each hour t = 1 … T)",
                        "Behaviour the model produces", "Assumptions",
                        "Limitations: what the results can and cannot say", "How to read the results"]:
            self.assertIn(heading, sections)
            self.assertTrue(sections[heading])

    def test_demonstration_scenarios_do_what_they_say(self):
        verdicts = [web.run(values).queue_trend()[0] for _, values, _ in web.DEMO_SCENARIOS]
        self.assertEqual(verdicts, ["QUEUE GROWING", "NO QUEUE", "BUILDS UP AND CLEARS REPEATEDLY",
                                    "QUEUE CLEARED", "QUEUE GROWING"])
        for _, values, _ in web.DEMO_SCENARIOS:
            self.assertEqual(web.validate_inputs(values)[1], [])
        self.assertTrue(set(web.OUTCOME_LEVEL) >= set(verdicts))


@unittest.skipIf(web is None, "web app libraries are not installed")
class TestCharts(unittest.TestCase):
    """Every chart is drawn from the simulation result, not from sample values."""

    def test_queue_chart(self):
        now, before = simulate(1100, 1000, 12), simulate(1200, 1000, 12)
        rows = chart_rows(web.queue_chart(now, before))
        this = [row["Vehicles waiting"] for row in rows if row["Run"] == "This run"]
        prev = [row["Vehicles waiting"] for row in rows if row["Run"] == "Previous run"]
        self.assertEqual(this, now.queue_line())
        self.assertEqual(prev, before.queue_line())
        single = chart_rows(web.queue_chart(now))
        self.assertEqual({row["Run"] for row in single}, {"This run"})

    def test_flow_chart(self):
        r = simulate(1100, 1000, 12)
        frame = web.flow_frame(r)
        inner = frame[~frame["Edge"]]
        arrivals = inner[inner["Series"] == "Vehicles arriving (after rerouting)"]
        capacity = inner[inner["Series"] == "Road capacity (after spillback)"]
        self.assertEqual(list(arrivals["Vehicles per hour"]), [h.arrivals for h in r.hourly])
        self.assertEqual(list(capacity["Vehicles per hour"]), [h.capacity for h in r.hourly])
        self.assertIn("Arrival rate setting", set(frame["Series"]))      # rerouting happened
        self.assertIn("Road capacity setting", set(frame["Series"]))     # spillback happened
        quiet = web.flow_frame(simulate(800, 1000, 6))                   # no feedback at all
        self.assertEqual(set(quiet["Series"]), {"Vehicles arriving (after rerouting)",
                                                "Road capacity (after spillback)"})
        self.assertTrue(chart_rows(web.flow_chart(r)))

    def test_condition_chart(self):
        r = simulate(1100, 1000, 12)
        rows = [row for row in chart_rows(web.condition_chart(r)) if "Traffic condition" in row]
        self.assertEqual([row["Demand ratio"] for row in rows], [h.demand_ratio for h in r.hourly])
        self.assertEqual([row["Traffic condition"] for row in rows], [h.condition for h in r.hourly])

    def test_long_and_extreme_runs_build(self):
        for args in [(1_000_000, 0.5, 720, 10_000_000), (0, 1000, 1, 0), (5000, 4000, 720, 0)]:
            r = simulate(*args)
            for chart in (web.queue_chart(r), web.flow_chart(r), web.condition_chart(r)):
                chart.to_dict()


if __name__ == "__main__":
    unittest.main()
