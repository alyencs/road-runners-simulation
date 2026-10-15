"""
Tests for the Streamlit web app (app.py), run headless with Streamlit's own test runner.

Run from the project folder with:   python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # streamlit not installed: only the terminal program's tests can run
    AppTest = None

from roadrunners.model import simulate  # noqa: E402

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


@unittest.skipIf(AppTest is None, "streamlit is not installed (pip install -r requirements.txt)")
class TestWebApp(unittest.TestCase):
    def setUp(self):
        self.at = AppTest.from_file(APP, default_timeout=60).run()
        self.assertEqual(len(self.at.exception), 0)

    def set_inputs(self, arrival, capacity, hours, start_queue):
        sidebar = self.at.sidebar
        sidebar.number_input(key="arrival_rate").set_value(float(arrival))
        sidebar.number_input(key="road_capacity").set_value(float(capacity))
        sidebar.number_input(key="hours").set_value(int(hours))
        sidebar.number_input(key="start_queue").set_value(int(start_queue))
        self.at.run()

    def click_run(self):
        [button] = [b for b in self.at.sidebar.button if b.label == "Run Simulation"]
        button.click().run()
        self.assertEqual(len(self.at.exception), 0, self.at.exception)

    def metrics(self):
        return {m.label: m.value for m in self.at.metric}

    def charts(self):
        # Streamlit 1.51 calls the element "arrow_vega_lite_chart"; newer versions "vega_lite_chart".
        return list(self.at.get("vega_lite_chart")) + list(self.at.get("arrow_vega_lite_chart"))

    def test_page_before_any_run(self):
        self.assertEqual(self.at.title[0].value, "ROAD RUNNERS")
        self.assertIn("Vehicle Arrival Rate and Road Capacity", self.at.subheader[0].value)
        self.assertEqual([t.label for t in self.at.tabs],
                         ["Results", "Hourly results table", "Compare with previous run", "How the model works"])
        self.assertTrue(any("No simulation has been run yet" in i.value for i in self.at.info))
        self.assertEqual(len(self.at.metric), 0)
        self.assertEqual(len(self.at.latex), 5)  # model explanation is available before running

    def test_default_run(self):
        self.click_run()
        m = self.metrics()
        r = simulate(1100, 1000, 12)
        self.assertEqual(m["Vehicles arriving"], f"{r.total_arrived:,.0f} veh")
        self.assertEqual(m["Vehicles passing through"], f"{r.total_served:,.0f} veh")
        self.assertEqual(m["Vehicles still waiting"], "505 veh")
        self.assertEqual(m["Longest queue"], "505 veh")
        self.assertEqual(m["Average waiting time"], "15.4 min")
        self.assertEqual(m["Worst traffic condition"], "Severe (LOS F)")
        self.assertTrue(any("Queue growing" in w.value for w in self.at.warning))
        self.assertTrue(any("Balanced: no vehicles were lost or created" in s.value for s in self.at.success))
        self.assertEqual(len(self.charts()), 3)
        table = self.at.dataframe[0].value
        self.assertEqual(list(table["Queue at end of hour (veh)"]), [h.queue for h in r.hourly])

    def test_other_valid_combinations(self):
        for args, verdict in [((1100, 1200, 12, 0), "No queue"),
                              ((800, 1000, 12, 500), "Queue cleared"),
                              ((1040, 1000, 24, 0), "Builds up and clears repeatedly"),
                              ((5000, 4000, 720, 0), "Queue growing")]:
            self.set_inputs(*args)
            self.click_run()
            r = simulate(*args)
            m = self.metrics()
            self.assertEqual(m["Vehicles still waiting"], f"{r.final_queue:,.0f} veh", args)
            self.assertEqual(m["Average waiting time"], f"{r.average_delay_minutes:,.1f} min", args)
            outcome = [e.value for e in list(self.at.success) + list(self.at.warning) + list(self.at.info)
                       if e.value.startswith("**Outcome:")]
            self.assertEqual(len(outcome), 1, args)
            self.assertIn(verdict, outcome[0], args)

    def test_invalid_input_is_rejected_with_a_message(self):
        self.set_inputs(1100, 0, 12, 0)
        self.click_run()
        self.assertEqual([e.value for e in self.at.sidebar.error],
                         ["Please enter a number greater than 0 for the road capacity (for example 1000)."])
        self.assertEqual(len(self.at.metric), 0)  # nothing was simulated

    def test_invalid_input_keeps_the_last_good_run(self):
        self.click_run()
        self.set_inputs(1100, 0, 12, 0)
        self.click_run()
        self.assertEqual(len(self.at.sidebar.error), 1)
        self.assertEqual(self.metrics()["Vehicles still waiting"], "505 veh")
        self.assertTrue(any("settings have changed" in i.value for i in self.at.info))

    def test_second_run_is_compared_with_the_first(self):
        self.click_run()
        self.assertTrue(any("Change one setting" in i.value for i in self.at.info))
        self.set_inputs(1200, 1000, 12, 0)
        self.click_run()
        deltas = {m.label: m.delta for m in self.at.metric}
        self.assertEqual(deltas["Vehicles still waiting"], "+1,075")   # 1,580 now vs 505 before
        self.assertEqual(self.at.markdown.values.count("#### Run 2 compared with run 1"), 1)
        [table] = self.at.table
        values = table.value
        self.assertIn("This run (run 2)", values.columns)
        self.assertIn("1,580", list(values["This run (run 2)"]))
        self.assertIn("505", list(values["Previous run (run 1)"]))
        self.assertEqual(len(self.charts()), 4)  # results charts + comparison chart

    def test_scenario_and_reset(self):
        self.at.sidebar.selectbox(key="scenario").set_value("4. Clearing an existing queue").run()
        self.assertEqual(self.at.sidebar.number_input(key="arrival_rate").value, 800.0)
        self.assertEqual(self.at.sidebar.number_input(key="start_queue").value, 500)
        self.click_run()
        self.assertEqual(self.metrics()["Longest queue"], "500 veh")
        [reset] = [b for b in self.at.sidebar.button if b.label == "Reset to example values"]
        reset.click().run()
        self.assertEqual(self.at.sidebar.number_input(key="arrival_rate").value, 1100.0)
        self.assertEqual(self.at.sidebar.number_input(key="start_queue").value, 0)


if __name__ == "__main__":
    unittest.main()
