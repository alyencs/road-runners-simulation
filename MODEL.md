# The Road Runners Model

## Purpose

To show how the **vehicle arrival rate** (demand) and the **road capacity** (supply)
decide whether a road bottleneck flows freely or builds a queue, and how congestion
then feeds back on itself.

## Why System Dynamics

Traffic at a bottleneck **accumulates**: vehicles that cannot pass do not disappear,
they wait and carry over to the next hour. Congestion also **changes behaviour**: drivers
reroute, and severe queues spill back and reduce what the road can pass. Accumulation
(a stock) and feedback loops are the two building blocks of System Dynamics, so it fits
this problem directly. The question is about aggregate traffic, not individual cars, so
a vehicle-by-vehicle model would add detail without answering it better.

## Structure

```
                     drivers reroute (B1, balancing)
                  ┌──────────────────────────────────┐
                  │                                  │
 vehicles  ──►  ARRIVALS  ──►  [ QUEUE (stock) ]  ──►  PASSED  (limited by CAPACITY)
                  ▲                  │                  ▲
                  │                  ▼                  │
                  └──── TRAFFIC CONDITION ──────────────┘
                       (from the demand ratio)    spillback reduces capacity (R2, reinforcing)
```

| Element | Type | Unit | Description |
|---|---|---|---|
| Queue | **stock** | vehicles | Vehicles waiting at the bottleneck at the end of each hour |
| Arrivals | inflow | vehicles/hour | Vehicles that join the road (arrival rate minus rerouted drivers) |
| Passed (served) | outflow | vehicles/hour | Vehicles that get through, at most the effective capacity |
| Demand ratio | auxiliary | – | (queue + arrivals) ÷ effective capacity |
| Traffic condition | auxiliary | Stable / Building / Severe | Read from the demand ratio; drives the feedback |
| Level of Service | indicator | A–F | Standard traffic grade of the same ratio (does not affect the dynamics) |

## Inputs (chosen by the user)

| Input | Symbol | Unit | Allowed range |
|---|---|---|---|
| Vehicle arrival rate | A | vehicles/hour | 0 – 1,000,000 |
| Road capacity | C | vehicles/hour | > 0 – 1,000,000 |
| Simulation duration | T | hours | 1 – 720 (whole) |
| Vehicles already waiting | Q(0) | vehicles | 0 – 10,000,000 (whole) |

The program starts with example values (A = 1,100, C = 1,000, T = 12, Q(0) = 0). They are
**illustrative**, not measured data, and any value in the allowed range can be used.

## Model rules (fixed assumptions)

| Rule | Value | Meaning |
|---|---|---|
| Time step | 1 hour | Flows are hourly totals |
| Stable | demand ratio ≤ 1.00 | The road can pass everyone who wants to pass |
| Building | 1.00 < ratio ≤ 1.20 | A queue is forming |
| Severe | ratio > 1.20 | Heavy congestion |
| Rerouting (loop B1) | Stable 0 %, Building 5 %, Severe 10 % of arriving drivers | Applied in the **next** hour |
| Spillback (loop R2) | Severe: 5 % of capacity lost | Applied in the **next** hour |
| Level of Service | A ≤ 0.35, B ≤ 0.54, C ≤ 0.77, D ≤ 0.93, E ≤ 1.00, F > 1.00 | Grade of the demand ratio |

The rerouting and spillback percentages are **modelling assumptions**. They were not
measured, and they set how strongly the feedback loops act. They live at the top of
`roadrunners/model.py`.

## Equations (each hour t = 1 … T)

```
1. Feedback from last hour:   d = rerouting share[condition(t-1)]     r = spillback share[condition(t-1)]
2. Flows:                     Arrivals(t)           = A × (1 − d)
                              Effective capacity(t) = C × (1 − r)
3. Demand ratio:              DR(t) = (Queue(t−1) + Arrivals(t)) / Effective capacity(t)
4. Classification:            condition(t), LOS(t) from DR(t)
5. Stock update:              Passed(t) = min(Queue(t−1) + Arrivals(t), Effective capacity(t))
                              Queue(t)  = Queue(t−1) + Arrivals(t) − Passed(t)
6. Waiting in the hour:       area under the queue line during the hour (vehicle-hours)
```

The condition before hour 1 comes from (Q(0) + A) / C.

**Average waiting time per vehicle** = total vehicle-hours of waiting ÷ (Q(0) + all
arrivals) × 60. Within each hour, arrivals and departures are assumed to be spread
evenly, so the queue changes in a straight line. If the queue empties part-way through
an hour, the line stops at zero. This is the standard way of measuring delay in
deterministic queueing.

**Worked example** (A = 1,100, C = 1,000, Q(0) = 0). Before hour 1 the ratio is
1,100/1,000 = 1.10, which is Building, so 5 % reroute: 1,045 arrive and 1,000 pass.
The queue grows by 45 every hour (45, 90, 135, 180, 225). In hour 5 the ratio
(180 + 1,045)/1,000 = 1.225 exceeds 1.20, which is Severe. Hour 6 therefore has 10 %
rerouting (990 arrive) and 5 % spillback (950 pass), and the queue reaches 265.

## Behaviour the model produces

All of these are calculated by the program, not entered by hand:

| Settings | Outcome |
|---|---|
| Arrival ≤ capacity | No queue ever forms |
| Arrival 1,100, capacity 1,000, 12 h | Queue grows to 505; average wait 15.4 min |
| Arrival 1,200, capacity 1,000, 12 h | Queue grows to 1,580; average wait 43.9 min |
| Arrival 1,040, capacity 1,000 | Builds up to 40 and clears, every 5 hours (rerouting holds it in check) |
| Arrival 800, capacity 1,000, 500 waiting | Existing queue clears by the end of hour 3 |

Without the feedback loops, the queue would simply grow by (A − C) vehicles every hour.
Rerouting slows that growth, and spillback speeds it up.

## Checks built into the model

* Passed ≤ queue + arrivals, and Passed ≤ effective capacity. A road cannot pass cars that are not there, or more than it can handle.
* The queue is never negative.
* Vehicle conservation: waiting at start + arrived = passed + still waiting. This is shown after every run.

## Assumptions

1. One bottleneck, simulated in one-hour steps, with traffic spread evenly within each hour.
2. Arrival rate and capacity are constant across the hours of a run. Only the feedback changes them.
3. Drivers who reroute leave the system. Other roads are not modelled.
4. Feedback reacts to the previous hour's condition with fixed percentages.
5. First come, first served, and no limit on queue length.
6. Arrivals are deterministic: the same inputs always give the same result.

## Limitations: what the results can and cannot say

* The model has **not been calibrated or validated against real traffic counts**. Its
  results show how this system behaves under the stated assumptions. They are not
  forecasts for a real road.
* The rerouting and spillback strengths are assumed. Different values would change the
  numbers, though the direction of their effect would not change.
* Below capacity the model gives zero delay. Real traffic also has random delays when a
  road is busy but not overloaded.
* The Level of Service shown is based on the demand ratio and is an indicator only.
  Formal traffic-engineering LOS uses other measures, such as delay at signals.

**What can be concluded:** whether a queue forms depends on the arrival rate relative to
the capacity, not on either value alone. Above capacity, the queue grows by roughly the
difference every hour. A queue persists after its cause is removed and takes time to
clear. Rerouting limits congestion, while spillback makes severe congestion worse.

**What cannot be concluded:** actual queue lengths or delays on a specific real road, or
the real-world size of the rerouting and spillback effects.
