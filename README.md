# ROAD RUNNERS: Traffic Flow Simulation

**How do the vehicle arrival rate and the road capacity affect traffic flow?**

A System Dynamics simulation of one road bottleneck, made for the final project in
Introduction to Modeling and Simulation (6IMODSIM), Holy Angel University.
`MODEL.md` explains the model itself.

---

## 1. Install (once)

You need **Python 3.9 or newer** ([python.org](https://www.python.org/downloads/)).
On Windows, tick **"Add python.exe to PATH"** during installation.

Open **PowerShell** in this folder. In File Explorer, open the `ROAD_RUNNERS` folder,
click the address bar, type `powershell`, and press Enter. Then run:

```powershell
py -m pip install -r requirements.txt
```

This installs **matplotlib**, the only extra library, used for the chart.

## 2. Run

```powershell
py road_runners.py
```

On macOS or Linux, use `python3 road_runners.py`.

## 3. How to use it

The program opens with a short description and one settings screen:

```
SIMULATION SETTINGS
  1  Vehicle arrival rate .........      1,100 vehicles/hour
  2  Road capacity ................      1,000 vehicles/hour
  3  Simulation duration ..........         12 hours
  4  Vehicles already waiting .....          0 vehicles
     Arrivals are 10% ABOVE capacity: more vehicles arrive than the road can pass.

  R    Run the simulation with these settings
  1-4  Change a setting (type its number)
  H    How the model works
  Q    Quit
```

* The values shown are **example starting values**, not required answers. Type a
  setting's number (1–4) to change it. The program shows the current value and the
  allowed range, and you can enter any value in that range. Pressing **Enter without
  typing** keeps the current value.
* Type **R** to run. The results appear immediately, and a chart window opens. Close
  the chart window to return to the settings.
* Change one setting and press **R** again. The new results are shown **next to the
  previous run**, and the chart draws the previous queue in grey, so the effect of the
  change is easy to see.
* **T** prints the hour-by-hour table of the last run. **H** explains the model. **Q** quits.

| Setting | Allowed values | Meaning |
|---|---|---|
| Vehicle arrival rate | 0 – 1,000,000 vehicles/hour (decimals allowed) | Vehicles that want to use the road each hour |
| Road capacity | more than 0 – 1,000,000 vehicles/hour (decimals allowed) | The most vehicles the road can let through each hour |
| Simulation duration | 1 – 720 hours (whole number) | How many one-hour steps to simulate |
| Vehicles already waiting | 0 – 10,000,000 vehicles (whole number) | A queue that exists at the start, for example after an accident |

The upper limits only reject values far beyond any single road. If a value is invalid,
the program says why in plain words (for example, *"Please enter a number of 0 or more
for the vehicle arrival rate"*) and asks again.

## 4. Reading the results

| Result | Meaning |
|---|---|
| Vehicles that arrived | Vehicles that joined the road during the simulation, after some drivers rerouted |
| Vehicles that passed through | Vehicles that got through the bottleneck |
| Vehicles still waiting at the end | The queue left when the simulation stops |
| Longest queue | The largest number of vehicles waiting at once |
| Average waiting time per vehicle | Total time all vehicles spent in the queue ÷ number of vehicles (minutes) |
| Worst traffic condition | The most congested hour: Stable / Building / Severe, with Level of Service A–F |
| Drivers who took another route | Effect of the **rerouting** feedback (congestion makes some drivers avoid the road) |
| Capacity lost to queue spillback | Effect of the **spillback** feedback (severe queues reduce what the road can pass) |
| OUTCOME | Whether the queue never formed, cleared, is growing, is shrinking, is stable, or builds up and clears repeatedly, with the reason |
| Vehicle check | Waiting at start + arrived = passed + still waiting. It shows that no vehicle was lost or created |

**The chart** (also saved as a PNG):
- **Top panel:** vehicles waiting in the queue, hour by hour. This is the main result:
  is the queue growing, stable or clearing?
- **Bottom panel:** vehicles arriving vs road capacity each hour. A queue grows whenever
  the blue line is above the orange line. The shaded areas show the rerouted drivers
  and the capacity lost to spillback.

Every run also saves its chart (`..._chart.png`) and hour-by-hour table (`..._hourly.csv`,
which opens in Excel) in the `results` folder. You can use them in the paper and slides.

## 5. Suggested demonstration

| Step | Change | What happens |
|---|---|---|
| 1 | Run the example (arrival 1,100, capacity 1,000) | Arrivals exceed capacity, so the queue **grows** every hour (505 vehicles after 12 h) |
| 2 | Set capacity to **1,200** and run | The road can pass everyone: **no queue**. Capacity decides whether a queue forms |
| 3 | Set capacity back to 1,000 and arrival to **1,040** and run | The queue **builds up and clears repeatedly**: rerouting drivers keep it in check |
| 4 | Set arrival to **800** and vehicles waiting to **500** and run | An existing queue **clears** within 3 hours once arrivals are below capacity |
| 5 | Set waiting back to 0 and arrival to **1,300** and run | A 30 % overload makes the queue grow much faster: **2,640** vehicles after 12 h instead of 505 |

## 6. Tests

```powershell
py -m unittest discover -s tests -v
```

The 21 automated tests check the model equations against hand calculations, vehicle
conservation on 500 random inputs, input validation, the queue verdicts, and that the
chart and saved table contain exactly the simulated values.

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `No module named 'matplotlib'` | Run `py -m pip install -r requirements.txt` in this folder. |
| `py` or `python` is not recognised | Install Python from python.org with "Add python.exe to PATH" ticked, then open a new PowerShell window. |
| `No module named 'roadrunners'` | Run the command from inside the `ROAD_RUNNERS` folder (the one containing `road_runners.py`). |
| The program seems to stop after a run | A chart window is open (it may be behind other windows). Close it to continue. |
| No chart window appears | The chart is still saved in the `results` folder. Windows only open when a screen is available. |

## 8. Files

```
ROAD_RUNNERS/
├── road_runners.py        start the program here
├── requirements.txt       the one extra library (matplotlib)
├── README.md              this file
├── MODEL.md               the model: variables, equations, assumptions, limitations
├── roadrunners/
│   ├── model.py           the simulation model (all equations)
│   ├── interface.py       settings screen, input checking, results screen
│   └── charts.py          the results chart
└── tests/test_model.py    automated tests
```
