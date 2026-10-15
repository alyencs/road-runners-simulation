"""
THE SIMULATION MODEL (System Dynamics) -- Road Runners

One road bottleneck is simulated in steps of one hour.

    Stock     Queue(t)            vehicles waiting at the bottleneck at the end of hour t
    Inflow    Arrivals(t)         vehicles that join during hour t   (after rerouting)
    Outflow   Served(t)           vehicles that pass during hour t   (at most the capacity)
    Feedback  Condition(t-1) -->  share of drivers who reroute       (loop B1, balancing)
              Condition(t-1) -->  share of capacity lost to spillback (loop R2, reinforcing)

For every hour t = 1 .. T:

  1. d = REROUTE_SHARE[condition(t-1)]      r = CAPACITY_LOSS[condition(t-1)]
  2. Arrivals(t)           = arrival rate x (1 - d)            x 1 h
     Effective capacity(t) = road capacity x (1 - r)           x 1 h
  3. Demand ratio(t)       = (Queue(t-1) + Arrivals(t)) / Effective capacity(t)
  4. Condition(t) and Level of Service(t) are read from the demand ratio
  5. Served(t)             = min(Queue(t-1) + Arrivals(t), Effective capacity(t))
     Queue(t)              = Queue(t-1) + Arrivals(t) - Served(t)
                           = max(0, Queue(t-1) + Arrivals(t) - Effective capacity(t))
  6. Waiting time in hour t = area under the queue line during the hour (vehicle-hours)

Every number the program shows is calculated here; nothing is typed in by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

HOUR = 1.0  # time step (hours). The demand ratio compares one hour of arrivals with one hour of capacity.

# --------------------------------------------------------------------------
# Model rules. These are ASSUMPTIONS of the model (not measured values).
# --------------------------------------------------------------------------
CONDITIONS: Tuple[str, ...] = ("Stable", "Building", "Severe")
STABLE_MAX = 1.00      # demand ratio <= 1.00 : the road can pass everything that wants to pass
BUILDING_MAX = 1.20    # 1.00 < ratio <= 1.20 : a queue is building; above 1.20 : severe


@dataclass(frozen=True)
class FeedbackRules:
    """Feedback strength for each traffic condition (Stable, Building, Severe)."""
    reroute_share: Tuple[float, float, float] = (0.00, 0.05, 0.10)   # loop B1
    capacity_loss: Tuple[float, float, float] = (0.00, 0.00, 0.05)   # loop R2


DEFAULT_RULES = FeedbackRules()
NO_FEEDBACK = FeedbackRules((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))  # used by tests to check the plain stock-flow equations

# Level of Service (A best ... F breakdown): upper demand-ratio bound of A, B, C, D, E.
LOS_BOUNDS: Tuple[float, ...] = (0.35, 0.54, 0.77, 0.93, 1.00)
LOS_LETTERS = "ABCDEF"


def classify_condition(ratio: float) -> str:
    """Stable / Building / Severe. Sets the feedback used in the NEXT hour."""
    if ratio <= STABLE_MAX:
        return "Stable"
    if ratio <= BUILDING_MAX:
        return "Building"
    return "Severe"


def classify_los(ratio: float) -> str:
    """Level of Service letter A-F from the demand ratio."""
    for letter, bound in zip(LOS_LETTERS, LOS_BOUNDS):
        if ratio <= bound:
            return letter
    return "F"


def waiting_in_hour(queue_start: float, arrivals: float, capacity: float) -> float:
    """Vehicle-hours spent waiting during one hour.

    Arrivals and departures are assumed to be spread evenly over the hour, so
    the queue changes in a straight line and stops at zero if it empties
    part-way. The result is the area under that line (trapezoid or triangle).
    """
    change_per_hour = (arrivals - capacity) / HOUR
    queue_end = queue_start + change_per_hour * HOUR
    if queue_end >= 0:                                   # queue never runs out during the hour
        return (queue_start + queue_end) / 2.0 * HOUR
    time_to_empty = queue_start / -change_per_hour       # queue empties before the hour ends
    return queue_start * time_to_empty / 2.0


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------
@dataclass
class Hour:
    hour: int
    rerouted: float          # drivers who took another route (vehicles)
    arrivals: float          # vehicles that joined the road (vehicles)
    capacity: float          # effective capacity this hour (vehicles)
    capacity_lost: float     # capacity lost to spillback (vehicles)
    demand_ratio: float      # (queue from last hour + arrivals) / capacity
    condition: str           # Stable / Building / Severe
    los: str                 # Level of Service A-F
    served: float            # vehicles that passed the bottleneck
    queue: float             # vehicles still waiting at the end of the hour
    waiting: float           # vehicle-hours of waiting during the hour


@dataclass
class Result:
    arrival_rate: float
    road_capacity: float
    hours: int
    start_queue: float
    hourly: List[Hour] = field(default_factory=list)

    def queue_line(self) -> List[float]:
        """Queue at hour 0, 1, ..., T (includes the starting queue)."""
        return [self.start_queue] + [h.queue for h in self.hourly]

    # ---- summary indicators (all derived from the hourly records) ----
    @property
    def total_arrived(self) -> float:
        return sum(h.arrivals for h in self.hourly)

    @property
    def total_served(self) -> float:
        return sum(h.served for h in self.hourly)

    @property
    def total_rerouted(self) -> float:
        return sum(h.rerouted for h in self.hourly)

    @property
    def total_capacity_lost(self) -> float:
        return sum(h.capacity_lost for h in self.hourly)

    @property
    def final_queue(self) -> float:
        return self.hourly[-1].queue

    @property
    def longest_queue(self) -> float:
        return max(self.queue_line())

    @property
    def average_delay_minutes(self) -> float:
        """Average waiting time per vehicle = total vehicle-hours waiting / vehicles.

        "Vehicles" = those already waiting at the start + all arrivals. Vehicles
        still queued when the simulation ends only count the waiting inside it.
        """
        vehicles = self.start_queue + self.total_arrived
        if vehicles <= 0:
            return 0.0
        return sum(h.waiting for h in self.hourly) / vehicles * 60.0

    @property
    def worst_hour(self) -> Hour:
        return max(self.hourly, key=lambda h: h.demand_ratio)

    @property
    def balance_error(self) -> float:
        """Vehicle conservation: start queue + arrivals - served - final queue (should be 0)."""
        return self.start_queue + self.total_arrived - self.total_served - self.final_queue

    def queue_trend(self) -> Tuple[str, str]:
        """A short verdict on how the queue behaved, plus a plain-language reason."""
        line = self.queue_line()
        last = self.hourly[-1]
        if max(line) <= 0:
            return ("NO QUEUE", "The road passed every arriving vehicle; nobody had to wait.")
        # Did the queue empty at some point and then form again afterwards?
        first_clear = next((i for i in range(1, len(line)) if line[i - 1] > 0 and line[i] == 0), None)
        rebuilt = first_clear is not None and any(
            line[i - 1] == 0 and line[i] > 0 for i in range(first_clear + 1, len(line)))
        if rebuilt:
            return ("BUILDS UP AND CLEARS REPEATEDLY",
                    "When the queue grows, drivers reroute and it clears; then they return and it builds again.")
        if self.final_queue == 0:
            cleared_at = max(i for i in range(1, len(line)) if line[i - 1] > 0)
            return ("QUEUE CLEARED", f"The waiting vehicles were cleared by the end of hour {cleared_at}.")
        change = last.queue - line[-2]
        if change > 1e-9:
            return ("QUEUE GROWING",
                    f"In the last hour {last.arrivals:,.0f} vehicles arrived but only {last.served:,.0f} could pass, "
                    f"so the queue grew by {change:,.0f}.")
        if change < -1e-9:
            return ("QUEUE SHRINKING",
                    f"The road is now passing more vehicles than arrive; the queue fell by {-change:,.0f} "
                    "in the last hour but has not cleared yet.")
        return ("QUEUE STABLE", "Arrivals and departures are balanced; the queue stayed the same in the last hour.")


# --------------------------------------------------------------------------
# The simulation
# --------------------------------------------------------------------------
def simulate(arrival_rate: float, road_capacity: float, hours: int, start_queue: float = 0.0,
             rules: FeedbackRules = DEFAULT_RULES) -> Result:
    """Run the model hour by hour and return every hourly value.

    arrival_rate   vehicles/hour that want to use the road (>= 0)
    road_capacity  vehicles/hour the road can pass (> 0)
    hours          number of one-hour steps (>= 1)
    start_queue    vehicles already waiting at hour 0 (>= 0)
    """
    if arrival_rate < 0 or road_capacity <= 0 or hours < 1 or start_queue < 0:
        raise ValueError("arrival_rate >= 0, road_capacity > 0, hours >= 1 and start_queue >= 0 are required")

    result = Result(arrival_rate, road_capacity, int(hours), start_queue)
    queue = start_queue
    # Condition before the first hour, from the starting queue and the base rates.
    condition = classify_condition((queue + arrival_rate * HOUR) / (road_capacity * HOUR))

    for t in range(1, int(hours) + 1):
        # 1. Feedback chosen by LAST hour's condition (drivers react with a delay)
        level = CONDITIONS.index(condition)
        reroute, loss = rules.reroute_share[level], rules.capacity_loss[level]

        # 2. Flows for this hour
        arrivals = arrival_rate * (1.0 - reroute) * HOUR
        capacity = road_capacity * (1.0 - loss) * HOUR

        # 3-4. How loaded the road is, and the resulting condition
        demand_ratio = (queue + arrivals) / capacity
        condition = classify_condition(demand_ratio)

        # 5. Stock update: cannot serve more than is waiting, nor more than the capacity
        queue_start = queue
        served = min(queue + arrivals, capacity)
        queue = queue + arrivals - served
        if queue < 1e-9:  # remove floating-point dust such as 1e-13
            queue = 0.0

        # 6. Waiting time accumulated during the hour
        waiting = waiting_in_hour(queue_start, arrivals, capacity)

        result.hourly.append(Hour(
            hour=t, rerouted=arrival_rate * HOUR - arrivals, arrivals=arrivals, capacity=capacity,
            capacity_lost=road_capacity * HOUR - capacity, demand_ratio=demand_ratio,
            condition=condition, los=classify_los(demand_ratio), served=served, queue=queue,
            waiting=waiting,
        ))
    return result
