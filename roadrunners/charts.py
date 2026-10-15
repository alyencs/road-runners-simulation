"""
The results chart (matplotlib): one figure, two panels, drawn only from simulation results.

  Top    : queue length over time (the main finding: growing, stable or clearing),
           with the previous run in grey for comparison.
  Bottom : vehicles arriving vs road capacity each hour, with the two feedback
           effects (rerouted drivers, capacity lost to spillback) shaded.

The terminal program shows and saves this figure after every run; the web app offers it
as the "Chart for slides (PNG)" download. The web app's interactive charts are in web.py
and reuse the colours defined here.
"""

from __future__ import annotations

from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from .interface import number
from .model import Result

BLUE, ORANGE, GREY, TEXT, TEXT_2, GRID = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "font.size": 11,
    "axes.edgecolor": "#b9b8b2", "axes.labelcolor": TEXT_2, "axes.titlecolor": TEXT,
    "axes.titlesize": 12, "axes.titleweight": "bold", "xtick.color": TEXT_2, "ytick.color": TEXT_2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})


def can_show_window() -> bool:
    """True when a screen is available to open a chart window."""
    return matplotlib.get_backend().lower() not in ("agg", "pdf", "ps", "svg", "cairo", "template")


def settings_label(r: Result) -> str:
    """The run's settings in words, e.g. "arrival 1,100 veh/h, capacity 1,000 veh/h"."""
    # number() keeps a decimal when the setting has one, so 999.9 vs 1,000 or a capacity
    # of 0.5 are not shown rounded to misleading values.
    text = f"arrival {number(r.arrival_rate)} veh/h, capacity {number(r.road_capacity)} veh/h"
    if r.start_queue > 0:
        text += f", {number(r.start_queue)} waiting at start"
    return text


def draw(result: Result, previous: Optional[Result] = None):
    """Build the figure and return it (the caller saves and/or shows it)."""
    verdict, _ = result.queue_trend()
    T = result.hours
    hours = np.arange(T + 1)
    markers = {"marker": "o", "markersize": 4} if T <= 48 else {}

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 8.5), sharex=False,
                                      gridspec_kw={"height_ratios": [3, 2]})
    fig.suptitle(f"Road Runners simulation: {settings_label(result)}, {T} h",
                 x=0.01, ha="left", fontsize=13, fontweight="bold", color=TEXT)

    # ---- Top: the queue -----------------------------------------------------------
    queue = result.queue_line()
    if previous is not None:
        prev_hours = np.arange(previous.hours + 1)
        top.plot(prev_hours, previous.queue_line(), color=GREY, lw=2,
                 label=f"Previous run ({settings_label(previous)})")
    top.fill_between(hours, queue, color=BLUE, alpha=0.12, lw=0)
    top.plot(hours, queue, color=BLUE, lw=2.5, label="This run", **markers)
    top.set_title(f"Vehicles waiting in the queue - {verdict.lower()}", loc="left")
    top.set_ylabel("Vehicles waiting")
    top.set_xlabel("Hour of the simulation")
    longest = max(queue + (previous.queue_line() if previous else []))
    top.set_ylim(0, max(10, longest * 1.45))   # headroom keeps the legend clear of the lines
    top.set_xlim(0, max(T, previous.hours if previous else 0))
    # Legend on the side away from this run's peak; the peak label points away from the legend.
    peak = int(np.argmax(queue))
    peak_on_left = peak <= T / 2
    if max(queue) > 0:
        top.annotate(f"longest queue: {queue[peak]:,.0f}", (peak, queue[peak]), textcoords="offset points",
                     xytext=(8, 8) if peak_on_left else (-8, 8), ha="left" if peak_on_left else "right",
                     fontsize=10, color=TEXT_2)
    top.legend(loc="upper right" if peak_on_left and max(queue) > 0 else "upper left", fontsize=10)

    # ---- Bottom: flows each hour (step lines: values are constant within an hour) --
    edges = np.arange(T + 1)
    arrivals = [h.arrivals for h in result.hourly]
    capacity = [h.capacity for h in result.hourly]

    def step(values):  # repeat the last value so the shaded area covers the final hour
        return np.append(values, values[-1])

    if result.total_rerouted > 0:
        bottom.fill_between(edges, step([result.arrival_rate] * T), step(arrivals), step="post",
                            color=BLUE, alpha=0.18, lw=0, label="Drivers who rerouted")
    if result.total_capacity_lost > 0:
        bottom.fill_between(edges, step([result.road_capacity] * T), step(capacity), step="post",
                            color=ORANGE, alpha=0.25, lw=0, label="Capacity lost to spillback")
    bottom.stairs(arrivals, edges, color=BLUE, lw=2.2, baseline=None, label="Vehicles arriving")
    bottom.stairs(capacity, edges, color=ORANGE, lw=2.2, baseline=None, label="Road capacity")
    bottom.set_title("Traffic flow each hour - a queue grows whenever arrivals are above capacity",
                     loc="left", fontsize=11)
    bottom.set_ylabel("Vehicles per hour")
    bottom.set_xlabel("Hour of the simulation")
    bottom.set_xlim(0, T)
    bottom.set_ylim(0, max(result.arrival_rate, result.road_capacity, 1) * 1.4)
    bottom.legend(loc="upper left", fontsize=9.5, ncol=2)

    fig.tight_layout()
    return fig
