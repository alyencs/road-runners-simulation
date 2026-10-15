"""
Helpers for the web app (app.py): input checking, tables and charts.

Nothing here changes the model. Inputs are checked with the same SETTINGS rules
as the terminal program, the simulation is model.simulate(), and every table and
chart is built from the Result it returns. There is no Streamlit code in this
file, so it can be tested on its own.
"""

from __future__ import annotations

import io
import re
from typing import Dict, List, Mapping, Optional, Tuple

import altair as alt
import pandas as pd

from .charts import BLUE, GREY, ORANGE
from .interface import FIELD, SETTINGS, Setting, check_value, number, summary_rows, write_csv
from .model import BUILDING_MAX, CONDITIONS, DEFAULT_RULES, LOS_BOUNDS, LOS_LETTERS, STABLE_MAX, Result, simulate

# Status colours for the traffic condition (good / warning / critical).
CONDITION_COLORS = {"Stable": "#0ca30c", "Building": "#fab219", "Severe": "#d03b3b"}

# The four inputs, keyed by the model's argument names.
INPUTS: Dict[str, Setting] = {FIELD[s.key]: s for s in SETTINGS}

# Steps from README section 5 ("Suggested demonstration").
DEMO_SCENARIOS: List[Tuple[str, Dict[str, float], str]] = [
    ("1. Arrivals 10% above capacity",
     {"arrival_rate": 1100.0, "road_capacity": 1000.0, "hours": 12, "start_queue": 0},
     "Arrivals exceed capacity, so the queue grows every hour."),
    ("2. More road capacity",
     {"arrival_rate": 1100.0, "road_capacity": 1200.0, "hours": 12, "start_queue": 0},
     "The road can pass everyone: no queue forms."),
    ("3. Arrivals just above capacity",
     {"arrival_rate": 1040.0, "road_capacity": 1000.0, "hours": 12, "start_queue": 0},
     "The queue builds up and clears repeatedly, because rerouting drivers keep it in check."),
    ("4. Clearing an existing queue",
     {"arrival_rate": 800.0, "road_capacity": 1000.0, "hours": 12, "start_queue": 500},
     "An existing queue clears within 3 hours once arrivals are below capacity."),
    ("5. A 30% overload",
     {"arrival_rate": 1300.0, "road_capacity": 1000.0, "hours": 12, "start_queue": 0},
     "The queue grows much faster than in step 1."),
]

# How prominent each outcome is in the app: "success", "warning" or "info".
OUTCOME_LEVEL = {
    "NO QUEUE": "success",
    "QUEUE CLEARED": "success",
    "QUEUE GROWING": "warning",
    "QUEUE SHRINKING": "info",
    "QUEUE STABLE": "info",
    "BUILDS UP AND CLEARS REPEATEDLY": "info",
}


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
def validate_inputs(raw: Mapping[str, object]) -> Tuple[Dict[str, float], List[str]]:
    """Check all four inputs. Returns (clean values, error messages); run only if there are no errors."""
    values: Dict[str, float] = {}
    errors: List[str] = []
    for field, setting in INPUTS.items():
        value, error = check_value(setting, raw.get(field))
        if error:
            errors.append(error)
        else:
            values[field] = value
    return values, errors


def run(values: Mapping[str, float]) -> Result:
    """Run the model with values that passed validate_inputs()."""
    return simulate(values["arrival_rate"], values["road_capacity"], int(values["hours"]), values["start_queue"])


def settings_label(r: Result) -> str:
    text = (f"arrival {number(r.arrival_rate)} veh/h, capacity {number(r.road_capacity)} veh/h, "
            f"{r.hours} h")
    if r.start_queue > 0:
        text += f", {number(r.start_queue)} waiting at start"
    return text


# --------------------------------------------------------------------------
# Numbers and tables
# --------------------------------------------------------------------------
def metric_cards(r: Result, prev: Optional[Result] = None) -> List[Dict[str, object]]:
    """The headline results. `delta` is the change from the previous run (None without one).

    delta_color "inverse" marks measures where an increase means more congestion.
    """
    worst = r.worst_hour

    def change(attr: str, fmt: str = "{:+,.0f}") -> Optional[str]:
        if prev is None:
            return None
        diff = getattr(r, attr) - getattr(prev, attr)
        return None if abs(diff) < 0.05 else fmt.format(diff)

    def card(label, value, delta, color, help_text):
        return {"label": label, "value": value, "delta": delta, "delta_color": color, "help": help_text}

    return [
        card("Vehicles arriving", f"{number(r.total_arrived)} veh",
             change("total_arrived"), "off",
             "Vehicles that joined the road during the simulation, after some drivers rerouted."),
        card("Vehicles passing through", f"{number(r.total_served)} veh",
             change("total_served"), "off",
             "Vehicles that got through the bottleneck."),
        card("Vehicles still waiting", f"{number(r.final_queue)} veh",
             change("final_queue"), "inverse",
             "The queue left when the simulation stops."),
        card("Longest queue", f"{number(r.longest_queue)} veh",
             change("longest_queue"), "inverse",
             "The largest number of vehicles waiting at once."),
        card("Average waiting time", f"{r.average_delay_minutes:,.1f} min",
             change("average_delay_minutes", "{:+,.1f} min"), "inverse",
             "Total time all vehicles spent in the queue ÷ number of vehicles (waiting at start + arrived)."),
        card("Worst traffic condition", f"{worst.condition} (LOS {worst.los})", None, "off",
             f"The most congested hour was hour {worst.hour} (demand ratio {worst.demand_ratio:.2f})."),
        card("Drivers who took another route", f"{number(r.total_rerouted)} veh",
             change("total_rerouted"), "off",
             "Effect of the rerouting feedback (loop B1): congestion makes some drivers avoid the road."),
        card("Capacity lost to spillback", f"{number(r.total_capacity_lost)} veh",
             change("total_capacity_lost"), "inverse",
             "Effect of the spillback feedback (loop R2): severe queues reduce what the road can pass."),
    ]


HOURLY_COLUMNS = {
    "hour": "Hour",
    "arrivals": "Vehicles arriving (veh)",
    "rerouted": "Drivers rerouted (veh)",
    "capacity": "Road capacity (veh)",
    "capacity_lost": "Capacity lost to spillback (veh)",
    "served": "Vehicles passed (veh)",
    "queue": "Queue at end of hour (veh)",
    "demand_ratio": "Demand ratio",
    "condition": "Traffic condition",
    "los": "Level of Service",
    "waiting": "Waiting (vehicle-hours)",
}


def hourly_frame(r: Result) -> pd.DataFrame:
    """One row per simulated hour, straight from Result.hourly."""
    rows = [{label: getattr(h, attr) for attr, label in HOURLY_COLUMNS.items()} for h in r.hourly]
    return pd.DataFrame(rows, columns=list(HOURLY_COLUMNS.values()))


def csv_text(r: Result) -> str:
    """The same CSV file the terminal program saves in the results folder."""
    buffer = io.StringIO()
    write_csv(r, buffer)
    return buffer.getvalue()


def comparison_frame(r: Result, prev: Result, run_no: int) -> pd.DataFrame:
    """This run next to the previous run, using the terminal program's results rows."""
    rows, group = [], ""
    for label, now, before in summary_rows(r, prev):
        if now is None:
            group = label
            continue
        rows.append({"": group, "Measure": label.strip(), f"This run (run {run_no})": now,
                     f"Previous run (run {run_no - 1})": before})
    return pd.DataFrame(rows)


def rules_frame() -> pd.DataFrame:
    """The fixed feedback rules, read from the model's constants."""
    ranges = (f"≤ {STABLE_MAX:.2f}", f"{STABLE_MAX:.2f} – {BUILDING_MAX:.2f}", f"> {BUILDING_MAX:.2f}")
    return pd.DataFrame({
        "Traffic condition": list(CONDITIONS),
        "Demand ratio": list(ranges),
        "Drivers who reroute next hour": [f"{x:.0%}" for x in DEFAULT_RULES.reroute_share],
        "Spillback: capacity lost next hour": [f"{x:.0%}" for x in DEFAULT_RULES.capacity_loss],
    })


def los_frame() -> pd.DataFrame:
    """Level of Service grades, read from the model's constants."""
    lower = [None] + list(LOS_BOUNDS)
    ranges = []
    for i, letter in enumerate(LOS_LETTERS):
        if i == 0:
            ranges.append(f"≤ {LOS_BOUNDS[0]:.2f}")
        elif i < len(LOS_BOUNDS):
            ranges.append(f"{lower[i]:.2f} – {LOS_BOUNDS[i]:.2f}")
        else:
            ranges.append(f"> {LOS_BOUNDS[-1]:.2f}")
    return pd.DataFrame({"Level of Service": list(LOS_LETTERS), "Demand ratio": ranges})


def doc_sections(markdown: str) -> Dict[str, str]:
    """Split MODEL.md into {"## heading": body} so the app can show its sections."""
    sections: Dict[str, str] = {}
    parts = re.split(r"^## +(.+)$", markdown, flags=re.MULTILINE)
    for heading, body in zip(parts[1::2], parts[2::2]):
        sections[heading.strip()] = body.strip()
    return sections


# --------------------------------------------------------------------------
# Charts (Altair; drawn only from the simulation result)
# --------------------------------------------------------------------------
HOUR_AXIS = alt.Axis(title="Hours since the start of the simulation", tickMinStep=1, format="d")


def queue_frame(r: Result, prev: Optional[Result] = None) -> pd.DataFrame:
    """Queue at hour 0..T for this run (and the previous run, if any)."""
    frames = []
    for label, result in (("This run", r), ("Previous run", prev)):
        if result is None:
            continue
        frames.append(pd.DataFrame({"Hour": range(result.hours + 1), "Vehicles waiting": result.queue_line(),
                                    "Run": label, "Settings": settings_label(result)}))
    return pd.concat(frames, ignore_index=True)


def queue_chart(r: Result, prev: Optional[Result] = None) -> alt.LayerChart:
    data = queue_frame(r, prev)
    runs = list(data["Run"].unique())
    colors = alt.Scale(domain=["This run", "Previous run"], range=[BLUE, GREY])
    dashes = alt.Scale(domain=["This run", "Previous run"], range=[[1, 0], [6, 4]])
    hover = alt.selection_point(fields=["Hour"], nearest=True, on="pointerover", empty=False, clear="pointerout")
    x = alt.X("Hour:Q", axis=HOUR_AXIS, scale=alt.Scale(domain=[0, int(data["Hour"].max())], nice=False))
    y = alt.Y("Vehicles waiting:Q", title="Vehicles waiting in the queue", scale=alt.Scale(domainMin=0))
    base = alt.Chart(data).encode(x=x, y=y)

    area = base.transform_filter(alt.datum.Run == "This run").mark_area(color=BLUE, opacity=0.12)
    legend = alt.Legend(title=None, orient="top-left") if len(runs) > 1 else None
    lines = base.mark_line(strokeWidth=2.5).encode(
        color=alt.Color("Run:N", scale=colors, legend=legend),
        strokeDash=alt.StrokeDash("Run:N", scale=dashes, legend=legend))
    points = base.mark_point(filled=True, size=70).encode(
        color=alt.Color("Run:N", scale=colors, legend=None),
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("Run:N"), alt.Tooltip("Settings:N"),
                 alt.Tooltip("Hour:Q", title="End of hour"),
                 alt.Tooltip("Vehicles waiting:Q", format=",.0f")],
    ).add_params(hover)
    rule = alt.Chart(data).mark_rule(color=GREY, strokeWidth=1).encode(x="Hour:Q").transform_filter(hover)
    return alt.layer(area, lines, rule, points).properties(height=340)


def flow_frame(r: Result) -> pd.DataFrame:
    """Vehicles per hour arriving and road capacity, one row per hour and series.

    Each value is the total for one one-hour step, so it is drawn as a flat
    step from the start to the end of that hour. The original settings are
    included only when a feedback loop changed them.
    """
    series = [("Vehicles arriving (after rerouting)", [h.arrivals for h in r.hourly]),
              ("Road capacity (after spillback)", [h.capacity for h in r.hourly])]
    if r.total_rerouted > 0:
        series.append(("Arrival rate setting", [r.arrival_rate] * r.hours))
    if r.total_capacity_lost > 0:
        series.append(("Road capacity setting", [r.road_capacity] * r.hours))
    rows = []
    for name, values in series:
        for t, value in enumerate(values, start=1):
            rows.append({"Start": t - 1, "Hour": t, "Series": name, "Vehicles per hour": value, "Edge": False})
        # Repeat the last value at the end of the final hour so its step is drawn in full.
        rows.append({"Start": r.hours, "Hour": r.hours, "Series": name, "Vehicles per hour": values[-1],
                     "Edge": True})
    return pd.DataFrame(rows)


FLOW_SERIES = ["Vehicles arriving (after rerouting)", "Road capacity (after spillback)",
               "Arrival rate setting", "Road capacity setting"]


def flow_chart(r: Result) -> alt.LayerChart:
    data = flow_frame(r)
    present = [s for s in FLOW_SERIES if s in set(data["Series"])]
    style = {FLOW_SERIES[0]: (BLUE, [1, 0]), FLOW_SERIES[1]: (ORANGE, [1, 0]),
             FLOW_SERIES[2]: (BLUE, [4, 4]), FLOW_SERIES[3]: (ORANGE, [4, 4])}
    colors = alt.Scale(domain=present, range=[style[s][0] for s in present])
    dashes = alt.Scale(domain=present, range=[style[s][1] for s in present])
    legend = alt.Legend(title=None, orient="bottom", columns=2, labelLimit=320)
    hover = alt.selection_point(fields=["Hour"], nearest=True, on="pointerover", empty=False, clear="pointerout")
    x = alt.X("Start:Q", axis=HOUR_AXIS, scale=alt.Scale(domain=[0, r.hours], nice=False))
    y = alt.Y("Vehicles per hour:Q", title="Vehicles per hour", scale=alt.Scale(zero=False, padding=12))

    lines = alt.Chart(data).mark_line(interpolate="step-after", strokeWidth=2.2).encode(
        x=x, y=y,
        color=alt.Color("Series:N", scale=colors, legend=legend, sort=present),
        strokeDash=alt.StrokeDash("Series:N", scale=dashes, legend=legend, sort=present),
        opacity=alt.condition(alt.FieldOneOfPredicate("Series", FLOW_SERIES[2:]), alt.value(0.7), alt.value(1)))

    # Invisible hover targets in the middle of each hour, carrying the tooltip.
    hourly = hourly_frame(r)
    hourly["Middle"] = hourly["Hour"] - 0.5
    targets = alt.Chart(hourly).mark_rule(strokeWidth=12, opacity=0).encode(
        x="Middle:Q",
        tooltip=[alt.Tooltip("Hour:Q"),
                 alt.Tooltip("Vehicles arriving (veh):Q", title="Vehicles arriving", format=",.0f"),
                 alt.Tooltip("Drivers rerouted (veh):Q", title="Drivers rerouted", format=",.0f"),
                 alt.Tooltip("Road capacity (veh):Q", title="Road capacity", format=",.0f"),
                 alt.Tooltip("Capacity lost to spillback (veh):Q", title="Capacity lost", format=",.0f"),
                 alt.Tooltip("Vehicles passed (veh):Q", title="Vehicles passed", format=",.0f")],
    ).add_params(hover)
    highlight = alt.Chart(hourly).mark_rule(color=GREY, strokeWidth=1).encode(x="Middle:Q").transform_filter(hover)
    return alt.layer(lines, highlight, targets).properties(height=360)


def condition_chart(r: Result) -> alt.LayerChart:
    """Demand ratio of every hour, coloured by the traffic condition it produces."""
    data = hourly_frame(r)
    inset = 0.08 if r.hours <= 48 else 0.0
    data["Start"] = data["Hour"] - 1 + inset
    data["End"] = data["Hour"] - inset
    present = [c for c in CONDITIONS if c in set(data["Traffic condition"])]
    colors = alt.Scale(domain=list(CONDITIONS), range=[CONDITION_COLORS[c] for c in CONDITIONS])

    bars = alt.Chart(data).mark_rect(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Start:Q", axis=HOUR_AXIS, scale=alt.Scale(domain=[0, r.hours], nice=False)),
        x2="End:Q",
        y=alt.Y("Demand ratio:Q", title="Demand ratio (queue + arrivals) ÷ capacity",
                scale=alt.Scale(domainMin=0)),
        y2=alt.datum(0),
        color=alt.Color("Traffic condition:N", scale=colors,
                        legend=alt.Legend(title="Traffic condition", orient="top", values=present)),
        tooltip=[alt.Tooltip("Hour:Q"), alt.Tooltip("Demand ratio:Q", format=".3f"),
                 alt.Tooltip("Traffic condition:N"), alt.Tooltip("Level of Service:N"),
                 alt.Tooltip("Queue at end of hour (veh):Q", title="Queue at end of hour", format=",.0f")])

    thresholds = pd.DataFrame({"Ratio": [STABLE_MAX, BUILDING_MAX],
                               "Meaning": ["Above this a queue builds (Building)",
                                           "Above this congestion is severe (Severe)"]})
    rules = alt.Chart(thresholds).mark_rule(color=GREY, strokeDash=[4, 4], strokeWidth=1.5).encode(
        y="Ratio:Q", tooltip=[alt.Tooltip("Ratio:Q", title="Demand ratio", format=".2f"), "Meaning:N"])
    return alt.layer(bars, rules).properties(height=320)
