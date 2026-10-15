"""
The text interface: one settings screen, one Run command, one results screen.

Input checking lives in SETTINGS / parse_value(); the model lives in model.py;
the chart lives in charts.py. This file only talks to the user.
"""

from __future__ import annotations

import csv
import datetime as _dt
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .model import Result, simulate

LINE = "=" * 70


# --------------------------------------------------------------------------
# The four inputs, their limits and their plain-language error messages
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Setting:
    key: str            # what the user types to change it
    name: str
    unit: str
    meaning: str
    low: float
    low_allowed: bool   # is `low` itself allowed?
    high: float
    whole: bool         # must be a whole number?
    error: str          # shown for any invalid entry


SETTINGS: List[Setting] = [
    Setting("1", "Vehicle arrival rate", "vehicles/hour",
            "how many vehicles want to use the road each hour", 0, True, 1_000_000, False,
            "Please enter a number of 0 or more for the vehicle arrival rate (for example 1200)."),
    Setting("2", "Road capacity", "vehicles/hour",
            "the most vehicles the road can let through each hour", 0, False, 1_000_000, False,
            "Please enter a number greater than 0 for the road capacity (for example 1000)."),
    Setting("3", "Simulation duration", "hours",
            "how many hours to simulate", 1, True, 720, True,
            "Please enter a whole number of hours from 1 to 720."),
    Setting("4", "Vehicles already waiting", "vehicles",
            "vehicles already queued when the simulation starts (e.g. after an accident)",
            0, True, 10_000_000, True,
            "Please enter a whole number of 0 or more for the vehicles already waiting (for example 0 or 500)."),
]
BY_KEY: Dict[str, Setting] = {s.key: s for s in SETTINGS}
FIELD = {"1": "arrival_rate", "2": "road_capacity", "3": "hours", "4": "start_queue"}

# Starting values only. Any value inside the allowed range can be used instead.
STARTING_VALUES = {"arrival_rate": 1100.0, "road_capacity": 1000.0, "hours": 12, "start_queue": 0}


def parse_value(setting: Setting, text: str) -> Tuple[Optional[float], Optional[str]]:
    """Return (value, None) for valid input or (None, message) for invalid input."""
    cleaned = text.strip().replace(",", "").replace("_", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None, setting.error
    if not math.isfinite(value):
        return None, setting.error
    too_low = value < setting.low or (value == setting.low and not setting.low_allowed)
    if too_low or (setting.whole and not value.is_integer()):
        return None, setting.error
    if value > setting.high:
        return None, (f"Please enter {setting.high:,.0f} or less for the {setting.name.lower()} "
                      "(larger values are far beyond a single road).")
    return (int(value) if setting.whole else value), None


def describe_range(s: Setting) -> str:
    low = f"{s.low:,.0f}" if s.low_allowed else f"more than {s.low:,.0f}"
    kind = "whole number " if s.whole else ""
    return f"any {kind}value from {low} to {s.high:,.0f}"


def number(x: float) -> str:
    """Whole vehicles when the value is whole, otherwise one decimal place."""
    return f"{x:,.0f}" if abs(x - round(x)) < 0.05 else f"{x:,.1f}"


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------
INTRO = f"""
{LINE}
  ROAD RUNNERS - Traffic Flow Simulation
  How do the vehicle arrival rate and the road capacity affect traffic?
{LINE}
  This System Dynamics model follows one road bottleneck, hour by hour.
  * Each hour, vehicles ARRIVE and the road lets through at most its CAPACITY.
  * Vehicles that cannot pass WAIT IN A QUEUE and carry over to the next hour.
  * Heavy congestion makes some drivers TAKE ANOTHER ROUTE, and severe queues
    SPILL BACK and slightly reduce the road's capacity.

  The settings below start with EXAMPLE values. You can change any of them
  (type its number), then type R to run the simulation and see the results."""

HELP = f"""
{LINE}
  HOW THE MODEL WORKS
{LINE}
  Queue at end of hour = queue from last hour + vehicles arriving - vehicles passing
  Vehicles passing     = whichever is smaller: (queue + arrivals) or road capacity

  Demand ratio = (queue from last hour + arrivals) / capacity
    1.00 or less  -> Stable   : the road can pass everyone who wants to pass
    1.00 to 1.20  -> Building : a queue is forming;   next hour 5% of drivers reroute
    above 1.20    -> Severe   : heavy congestion;     next hour 10% of drivers reroute
                                                       and capacity drops by 5% (spillback)
  Drivers react one hour later, because they need time to notice the congestion.
  Level of Service (LOS) grades the same ratio from A (free flow) to F (breakdown).

  Average waiting time per vehicle = total time all vehicles spent in the queue
  divided by the number of vehicles (waiting at the start + arrived).

  The rerouting and spillback percentages are model assumptions, and the
  settings are example values, not measured traffic data. The results show how
  the system behaves under these assumptions; they are not a forecast for a real road.
{LINE}"""


def settings_screen(values: Dict[str, float], has_result: bool) -> str:
    rows = ["", "SIMULATION SETTINGS"]
    for s in SETTINGS:
        shown = number(values[FIELD[s.key]])
        rows.append(f"  {s.key}  {s.name + ' ':.<30} {shown:>10} {s.unit}")
    ratio = values["arrival_rate"] / values["road_capacity"]
    if ratio > 1:
        hint = f"Arrivals are {ratio - 1:.0%} ABOVE capacity: more vehicles arrive than the road can pass."
    elif ratio < 1:
        hint = f"Arrivals are {1 - ratio:.0%} below capacity: the road can pass every arriving vehicle."
    else:
        hint = "Arrivals exactly equal capacity."
    rows += [f"     {hint}", "",
             "  R    Run the simulation with these settings",
             "  1-4  Change a setting (type its number)"]
    if has_result:
        rows.append("  T    Show the hour-by-hour table of the last run")
    rows += ["  H    How the model works", "  Q    Quit"]
    return "\n".join(rows)


def results_screen(run_no: int, r: Result, prev: Optional[Result]) -> str:
    worst = r.worst_hour
    rows = [("Settings", None, None),
            ("  Vehicle arrival rate (vehicles/hour)", number(r.arrival_rate), prev and number(prev.arrival_rate)),
            ("  Road capacity (vehicles/hour)", number(r.road_capacity), prev and number(prev.road_capacity)),
            ("  Simulation duration (hours)", str(r.hours), prev and str(prev.hours)),
            ("  Vehicles already waiting at the start", number(r.start_queue), prev and number(prev.start_queue)),
            ("What happened", None, None),
            ("  Vehicles that arrived", number(r.total_arrived), prev and number(prev.total_arrived)),
            ("  Vehicles that passed through", number(r.total_served), prev and number(prev.total_served)),
            ("  Vehicles still waiting at the end", number(r.final_queue), prev and number(prev.final_queue)),
            ("  Longest queue (vehicles)", number(r.longest_queue), prev and number(prev.longest_queue)),
            ("  Average waiting time per vehicle (min)", f"{r.average_delay_minutes:,.1f}",
             prev and f"{prev.average_delay_minutes:,.1f}"),
            ("  Worst traffic condition", f"{worst.condition} (LOS {worst.los})",
             prev and f"{prev.worst_hour.condition} (LOS {prev.worst_hour.los})"),
            ("Feedback effects", None, None),
            ("  Drivers who took another route", number(r.total_rerouted), prev and number(prev.total_rerouted)),
            ("  Capacity lost to queue spillback (veh)", number(r.total_capacity_lost),
             prev and number(prev.total_capacity_lost))]

    out = ["", LINE, f"  RESULTS - run {run_no}", LINE]
    out.append(f"  {'':<42}{'This run':>16}" + (f"{'Previous run':>17}" if prev else ""))
    for label, now, before in rows:
        if now is None:
            out.append(f"  {label}")
        else:
            out.append(f"  {label:<42}{now:>16}" + (f"{before:>17}" if prev else ""))

    verdict, reason = r.queue_trend()
    out += ["", f"  OUTCOME: {verdict}", f"  {reason}", "",
            f"  Vehicle check: {number(r.start_queue)} waiting at start + {number(r.total_arrived)} arrived"
            f" = {number(r.total_served)} passed + {number(r.final_queue)} still waiting"
            + ("  (balanced: no vehicles lost or created)" if abs(r.balance_error) < 1e-6 else "  (NOT BALANCED)")]
    return "\n".join(out)


def hourly_table(r: Result) -> str:
    head = (f"  {'Hour':>4} {'Arrived':>10} {'Rerouted':>9} {'Capacity':>10} {'Passed':>10} "
            f"{'Waiting':>10} {'Demand':>7}  Condition")
    sub = f"  {'':>4} {'(veh)':>10} {'(veh)':>9} {'(veh)':>10} {'(veh)':>10} {'at end':>10} {'ratio':>7}"
    lines = ["", f"  HOUR-BY-HOUR RESULTS (arrival {number(r.arrival_rate)} veh/h, "
                 f"capacity {number(r.road_capacity)} veh/h, {number(r.start_queue)} waiting at start)",
             head, sub, "  " + "-" * 82]
    for h in r.hourly:
        lines.append(f"  {h.hour:>4} {number(h.arrivals):>10} {number(h.rerouted):>9} {number(h.capacity):>10} "
                     f"{number(h.served):>10} {number(h.queue):>10} {h.demand_ratio:>7.2f}  "
                     f"{h.condition} (LOS {h.los})")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Saving results (for the report and slides)
# --------------------------------------------------------------------------
def save_csv(r: Result, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["hour", "vehicles_arrived", "drivers_rerouted", "capacity_veh", "capacity_lost_veh",
                         "vehicles_passed", "queue_at_end", "demand_ratio", "condition", "level_of_service",
                         "waiting_vehicle_hours"])
        for h in r.hourly:
            writer.writerow([h.hour, h.arrivals, h.rerouted, h.capacity, h.capacity_lost, h.served,
                             h.queue, round(h.demand_ratio, 4), h.condition, h.los, h.waiting])


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
class Quit(Exception):
    pass


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        raise Quit() from None


def change_setting(values: Dict[str, float], s: Setting) -> None:
    field = FIELD[s.key]
    current = number(values[field])
    print(f"\n  {s.name}: {s.meaning}.")
    print(f"  Current value: {current} {s.unit}. You can enter {describe_range(s)}.")
    while True:
        text = ask(f"  New {s.name.lower()} ({s.unit}), or press Enter to keep {current}: ")
        if not text:
            print(f"  Kept {current} {s.unit}.")
            return
        value, error = parse_value(s, text)
        if error:
            print(f"  ! {error}")
            continue
        values[field] = value
        print(f"  {s.name} changed from {current} to {number(value)} {s.unit}. "
              "Type R to see how this changes the traffic.")
        return


def run(values: Dict[str, float], run_no: int, previous: Optional[Result], results_dir: str,
        stamp: str, show_chart: bool) -> Result:
    from . import charts
    import matplotlib.pyplot as plt

    result = simulate(values["arrival_rate"], values["road_capacity"], int(values["hours"]),
                      values["start_queue"])
    print(results_screen(run_no, result, previous))

    os.makedirs(results_dir, exist_ok=True)
    base = os.path.join(results_dir, f"{stamp}_run{run_no}")
    fig = charts.draw(result, previous)
    fig.savefig(base + "_chart.png", dpi=130, bbox_inches="tight")
    save_csv(result, base + "_hourly.csv")
    print(f"\n  Saved in '{os.path.basename(results_dir)}' folder: "
          f"{os.path.basename(base)}_chart.png and {os.path.basename(base)}_hourly.csv")
    if show_chart and charts.can_show_window():
        print("  A chart window has opened. Close it to return to the settings.")
        plt.show()
    plt.close(fig)
    print("  Tip: change one setting (1-4) and press R again - the results will be shown side by side.")
    return result


def main(results_dir: Optional[str] = None, show_chart: bool = True) -> int:
    results_dir = results_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                              "results")
    stamp = _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    values = dict(STARTING_VALUES)
    last: Optional[Result] = None   # the most recent run; shown as "Previous run" next time
    run_no = 0
    print(INTRO)
    try:
        while True:
            print(settings_screen(values, last is not None))
            choice = ask("\nYour choice: ").upper()
            if choice == "R":
                run_no += 1
                last = run(values, run_no, last, results_dir, stamp, show_chart)
            elif choice in BY_KEY:
                change_setting(values, BY_KEY[choice])
            elif choice == "T" and last is not None:
                print(hourly_table(last))
            elif choice == "H":
                print(HELP)
            elif choice == "Q":
                break
            else:
                options = "R, 1, 2, 3, 4, " + ("T, " if last is not None else "") + "H or Q"
                print(f"  ! Please type {options}.")
    except (Quit, KeyboardInterrupt):
        print()
    print("\nThank you for using Road Runners. Goodbye.")
    return 0
