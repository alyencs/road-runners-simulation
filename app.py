"""
ROAD RUNNERS - web app (Streamlit entry point; Streamlit Community Cloud runs this file).
The Impact of Vehicle Arrival Rate and Road Capacity on Traffic Flow.

Run locally with:   streamlit run app.py

This file only lays out the page. When Run Simulation is pressed:
  1. web.validate_inputs() checks the four settings with the rules in interface.py;
  2. interface.simulate_settings() runs model.simulate(), the same model the terminal program uses;
  3. the Result is kept in st.session_state ("current", and the run before it as "previous"),
     and every metric, table and chart below is built from it by roadrunners/web.py.
Streamlit re-runs this whole script after every click, so anything that must survive between
runs (the settings and the last two results) lives in st.session_state.
"""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw charts off-screen on the server

import matplotlib.pyplot as plt  # noqa: E402
import streamlit as st  # noqa: E402

from roadrunners import charts, web  # noqa: E402
from roadrunners.interface import (STARTING_VALUES, describe_range, load_hint, simulate_settings,  # noqa: E402
                                   vehicle_check)
from roadrunners.model import BUILDING_MAX, STABLE_MAX  # noqa: E402

HERE = Path(__file__).resolve().parent

st.set_page_config(page_title="ROAD RUNNERS – Traffic Flow Simulation", page_icon="🚗", layout="wide")

# Widget settings for the four inputs. Limits come from interface.SETTINGS (via web.INPUTS).
# Road capacity's lower limit is exclusive (it must be more than 0), so 0 can be typed
# and is then rejected with the model's own message.
WIDGETS = {
    "arrival_rate": {"label": "Vehicle arrival rate (vehicles/hour)", "step": 50.0, "format": "%.1f"},
    "road_capacity": {"label": "Road capacity (vehicles/hour)", "step": 50.0, "format": "%.1f"},
    "hours": {"label": "Simulation duration (hours)", "step": 1, "format": "%d"},
    "start_queue": {"label": "Initial queue (vehicles already waiting)", "step": 50, "format": "%d"},
}


# --------------------------------------------------------------------------
# Session state: widget values, the latest run and the run before it
# --------------------------------------------------------------------------
def widget_value(field: str, value: float):
    """Whole-number settings use int widgets, the others float widgets (Streamlit needs one type)."""
    return int(value) if web.INPUTS[field].whole else float(value)


for _field, _value in STARTING_VALUES.items():
    st.session_state.setdefault(_field, widget_value(_field, _value))
st.session_state.setdefault("current", None)    # {"run_no", "result", "png"}
st.session_state.setdefault("previous", None)   # the run before it, for comparison
st.session_state.setdefault("run_count", 0)


def apply_values(values) -> None:
    for field, value in values.items():
        st.session_state[field] = widget_value(field, value)


def chart_png(result, previous) -> bytes:
    """The terminal program's results chart, as a PNG for slides."""
    figure = charts.draw(result, previous)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=130, bbox_inches="tight")
    plt.close(figure)
    return buffer.getvalue()


def load_scenario() -> None:
    choice = st.session_state.get("scenario")
    for name, values, _ in web.DEMO_SCENARIOS:
        if name == choice:
            apply_values(values)


def reset_values() -> None:
    apply_values(STARTING_VALUES)
    st.session_state["scenario"] = None


# --------------------------------------------------------------------------
# Sidebar: settings and the Run button
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("Simulation settings")
    st.caption("The starting values are **examples**, not measured data. Change any of them, "
               "then press **Run Simulation**.")

    st.selectbox("Load a demonstration scenario (optional)", [name for name, _, _ in web.DEMO_SCENARIOS],
                 index=None, key="scenario", on_change=load_scenario,
                 placeholder="Choose a scenario…",
                 help="Fills in the settings for one step of the suggested demonstration. "
                      "Press Run Simulation afterwards.")
    for name, _, description in web.DEMO_SCENARIOS:
        if name == st.session_state.get("scenario"):
            st.caption(f"Expected: {description}")

    for field, widget in WIDGETS.items():
        setting = web.INPUTS[field]
        st.number_input(
            widget["label"], key=field, step=widget["step"], format=widget["format"],
            min_value=widget_value(field, setting.low), max_value=widget_value(field, setting.high),
            help=f"{setting.meaning[0].upper() + setting.meaning[1:]}. Allowed: {describe_range(setting)} "
                 f"{setting.unit}.")

    raw = {field: st.session_state[field] for field in WIDGETS}
    if raw["road_capacity"] > 0:
        st.caption(load_hint(raw["arrival_rate"], raw["road_capacity"]))

    run_clicked = st.button("Run Simulation", type="primary", width="stretch")
    st.button("Reset to example values", on_click=reset_values, width="stretch")

    if run_clicked:
        values, errors = web.validate_inputs(raw)
        if errors:
            for message in errors:
                st.error(message)
        else:
            st.session_state.run_count += 1
            previous_run = st.session_state.current
            result_now = simulate_settings(values)
            st.session_state.previous = previous_run
            st.session_state.current = {
                "run_no": st.session_state.run_count, "result": result_now,
                "png": chart_png(result_now, previous_run["result"] if previous_run else None)}

    with st.expander("Fixed model rules (not adjustable)"):
        st.caption("These are assumptions built into the model (`roadrunners/model.py`). "
                   "They apply to every run.")
        st.dataframe(web.rules_frame(), hide_index=True, width="stretch")
        st.caption("Time step: 1 hour. Feedback reacts to the **previous** hour's condition.")


# --------------------------------------------------------------------------
# Page header
# --------------------------------------------------------------------------
st.title("ROAD RUNNERS")
st.subheader("The Impact of Vehicle Arrival Rate and Road Capacity on Traffic Flow")
st.markdown(
    "This System Dynamics simulation follows **one road bottleneck, hour by hour**. Each hour, vehicles "
    "**arrive** and the road lets through at most its **capacity**. Vehicles that cannot pass **wait in a "
    "queue** and carry over to the next hour. Heavy congestion makes some drivers **take another route**, "
    "and severe queues **spill back** and reduce the road's capacity. Choose the settings in the sidebar "
    "and press **Run Simulation** to see whether a queue forms, how long it gets and how long drivers wait.")
st.caption("6IMODSIM final project · Introduction to Modeling and Simulation · Holy Angel University")

current = st.session_state.current
previous = st.session_state.previous
result = current["result"] if current else None
prev_result = previous["result"] if previous else None

if result is not None:
    ran_with = {"arrival_rate": result.arrival_rate, "road_capacity": result.road_capacity,
                "hours": result.hours, "start_queue": result.start_queue}
    if any(float(raw[f]) != float(ran_with[f]) for f in ran_with):
        st.info("The settings have changed since the last run. Press **Run Simulation** to update the results.")

tab_results, tab_table, tab_compare, tab_model = st.tabs(
    ["Results", "Hourly results table", "Compare with previous run", "How the model works"])


def no_run_yet() -> None:
    st.info("No simulation has been run yet. Choose the settings in the sidebar and press **Run Simulation**. "
            "On a phone, tap the **>>** arrow at the top left to open the sidebar.")


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------
with tab_results:
    if result is None:
        no_run_yet()
    else:
        st.markdown(f"#### Run {current['run_no']}: {web.settings_label(result)}")
        verdict, reason = result.queue_trend()
        getattr(st, web.OUTCOME_LEVEL[verdict])(f"**Outcome: {verdict.capitalize()}.** {reason}")

        cards = web.metric_cards(result, prev_result)
        for row_start in (0, 3):
            for column, card in zip(st.columns(3), cards[row_start:row_start + 3]):
                column.metric(card["label"], card["value"], card["delta"], delta_color=card["delta_color"],
                              help=card["help"], border=True)
        if prev_result is not None:
            st.caption(f"Small figures under the values show the change from the previous run "
                       f"(run {previous['run_no']}). Red means more congestion.")

        st.markdown("##### Feedback effects")
        feedback = st.columns(3)
        for column, card in zip(feedback, cards[6:8]):
            column.metric(card["label"], card["value"], card["delta"], delta_color=card["delta_color"],
                          help=card["help"], border=True)
        check, balanced = vehicle_check(result)
        with feedback[2]:
            if balanced:
                st.success(f"**Vehicle check:** {check}. Balanced: no vehicles were lost or created.")
            else:
                st.error(f"**Vehicle check:** {check}. NOT BALANCED.")

        st.markdown("##### Vehicles waiting in the queue")
        st.caption("The queue at the end of each hour (hour 0 is the start). This is the main result: "
                   "is the queue growing, stable or clearing?"
                   + (" The dashed grey line is the previous run." if prev_result is not None else ""))
        st.altair_chart(web.queue_chart(result, prev_result), width="stretch")

        st.markdown("##### Vehicles arriving vs road capacity")
        st.caption("Both are **vehicles per hour**: each flat step is the total for one one-hour step of the "
                   "model. The queue grows in every hour where the blue line is above the orange line. "
                   "Dashed lines (when shown) are the original settings: the gap between them and the solid "
                   "lines is the drivers who rerouted (blue) and the capacity lost to spillback (orange).")
        st.altair_chart(web.flow_chart(result), width="stretch")

        st.markdown("##### Traffic condition each hour")
        st.caption("The demand ratio compares the vehicles that want to pass (queue + arrivals) with the "
                   "capacity. The colour shows the traffic condition it gives, which decides the "
                   "rerouting and spillback in the **next** hour. The dashed lines mark the limits: above "
                   f"{STABLE_MAX:.2f} a queue builds, above {BUILDING_MAX:.2f} congestion is severe. "
                   "Hover a bar for its Level of Service.")
        st.altair_chart(web.condition_chart(result), width="stretch")

        st.markdown("##### Download")
        left, right, _ = st.columns([1, 1, 2])
        left.download_button("Hourly results (CSV)", web.csv_text(result),
                             file_name=f"road_runners_run{current['run_no']}_hourly.csv", mime="text/csv",
                             key="csv_results", width="stretch")
        right.download_button("Chart for slides (PNG)", current["png"],
                              file_name=f"road_runners_run{current['run_no']}_chart.png", mime="image/png",
                              key="png_results", width="stretch")


# --------------------------------------------------------------------------
# Hourly table
# --------------------------------------------------------------------------
with tab_table:
    if result is None:
        no_run_yet()
    else:
        st.markdown(f"#### Hour-by-hour results, run {current['run_no']}")
        st.caption(f"{web.settings_label(result)}. Every value is calculated by the model; "
                   "flows are totals for each one-hour step.")
        fmt = {column: st.column_config.NumberColumn(format="%.1f") for column in web.HOURLY_COLUMNS.values()
               if "(veh)" in column or "vehicle-hours" in column}
        fmt["Demand ratio"] = st.column_config.NumberColumn(format="%.3f")
        fmt["Hour"] = st.column_config.NumberColumn(format="%d")
        st.dataframe(web.hourly_frame(result), hide_index=True, width="stretch", column_config=fmt)
        st.download_button("Download this table (CSV)", web.csv_text(result),
                           file_name=f"road_runners_run{current['run_no']}_hourly.csv", mime="text/csv",
                           key="csv_table")


# --------------------------------------------------------------------------
# Comparison with the previous run (as in the terminal program)
# --------------------------------------------------------------------------
with tab_compare:
    if result is None:
        no_run_yet()
    elif prev_result is None:
        st.info("Change one setting in the sidebar and press **Run Simulation** again. The new results will "
                "be shown next to this run, so the effect of the change is easy to see.")
    else:
        st.markdown(f"#### Run {current['run_no']} compared with run {previous['run_no']}")
        st.table(web.comparison_frame(result, prev_result, current["run_no"]).set_index(""))
        prev_verdict, _ = prev_result.queue_trend()
        st.markdown(f"**Outcome:** this run: *{result.queue_trend()[0].capitalize()}*; "
                    f"previous run: *{prev_verdict.capitalize()}*.")
        st.altair_chart(web.queue_chart(result, prev_result), width="stretch")


# --------------------------------------------------------------------------
# The model, explained (sections come from MODEL.md)
# --------------------------------------------------------------------------
with tab_model:
    model_doc = (HERE / "MODEL.md").read_text(encoding="utf-8")
    doc = web.doc_sections(model_doc)

    st.markdown("#### In plain words")
    st.markdown(
        "Think of the road as a **bucket with a hole**. Vehicles pour in at the **arrival rate**; the hole "
        "lets out at most the **road capacity** each hour. If more pours in than can drain, the bucket fills "
        "up: that is the **queue**. Vehicles are never lost, they just wait and leave later. The queue is the "
        "model's **stock** (an accumulation); arrivals and passing vehicles are its **flows**.\n\n"
        "Drivers also react to congestion. When the road is busy, some choose **another route** (fewer "
        "arrivals), and a severe queue **spills back** and blocks the road (less capacity). These are the "
        "model's two **feedback loops**.")

    st.markdown("#### Main system variables")
    st.markdown(doc["Structure"])
    st.markdown(doc["Inputs (chosen by the user)"])

    st.markdown("#### How the simulation works: the equations for each hour t")
    st.markdown("**1. Feedback from the previous hour** sets the rerouting share *d* and the spillback "
                "share *r* (see the rules below).")
    st.latex(r"\text{Arrivals}_t = A\,(1 - d_t) \qquad \text{Capacity}_t = C\,(1 - r_t)")
    st.markdown("**2. Demand ratio**: how many vehicles want to pass compared with how many can.")
    st.latex(r"DR_t = \frac{Q_{t-1} + \text{Arrivals}_t}{\text{Capacity}_t}")
    st.markdown("**3. Stock update**: the road cannot pass vehicles that are not there, or more than "
                "its capacity.")
    st.latex(r"\text{Passed}_t = \min\left(Q_{t-1} + \text{Arrivals}_t,\ \text{Capacity}_t\right)"
             r"\qquad Q_t = Q_{t-1} + \text{Arrivals}_t - \text{Passed}_t")
    st.markdown("**4. Waiting time**: within each hour the queue changes in a straight line, so the "
                "vehicle-hours of waiting *W* are the area under the queue line (stopping at zero if the "
                "queue empties part-way).")
    st.latex(r"\text{Average wait (min)} = \frac{\sum_t W_t}{Q_0 + \sum_t \text{Arrivals}_t}\times 60")
    st.markdown("**5. Vehicle balance**: checked after every run.")
    st.latex(r"Q_0 + \sum_t \text{Arrivals}_t = \sum_t \text{Passed}_t + Q_T")
    st.caption("$A$ = vehicle arrival rate, $C$ = road capacity, $Q$ = queue ($Q_0$ = initial queue, "
               "$Q_T$ = queue at the end), $t$ = hour 1 … $T$.")
    with st.expander("The same equations as written in MODEL.md, with a worked example"):
        st.markdown(doc["Equations (each hour t = 1 … T)"])

    st.markdown("#### Feedback loops")
    st.markdown(
        "- **B1 Rerouting (balancing loop):** more congestion → more drivers take another route → fewer "
        "arrivals → less congestion. It *limits* the queue.\n"
        "- **R2 Spillback (reinforcing loop):** severe congestion → the queue blocks the road → less "
        "capacity → even more congestion. It *makes severe congestion worse*.\n\n"
        "Drivers react **one hour later**, because they need time to notice the congestion. The traffic "
        "condition in each hour comes from the demand ratio:")
    left, right = st.columns([3, 2])
    left.dataframe(web.rules_frame(), hide_index=True, width="stretch")
    right.dataframe(web.los_frame(), hide_index=True, width="stretch")
    st.caption("The Level of Service (A = free flow … F = breakdown) grades the same demand ratio. "
               "It is an indicator only and does not affect the dynamics.")
    st.markdown(doc["Behaviour the model produces"])

    st.markdown("#### Assumptions")
    st.markdown(doc["Assumptions"])
    st.markdown("#### Limitations: what the results can and cannot say")
    st.markdown(doc["Limitations: what the results can and cannot say"])
    st.markdown("#### How to read the results")
    st.markdown(doc["How to read the results"])

    with st.expander("Full model documentation (MODEL.md)"):
        st.markdown(model_doc)
