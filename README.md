# ROAD RUNNERS: Traffic Flow Simulation

**The Impact of Vehicle Arrival Rate and Road Capacity on Traffic Flow**

A System Dynamics simulation of one road bottleneck, made for the final project in
Introduction to Modeling and Simulation (6IMODSIM), Holy Angel University.
`MODEL.md` explains the model itself.

The simulation can be used in two ways. Both run the same model (`roadrunners/model.py`):

| | Web app (`app.py`) | Terminal program (`road_runners.py`) |
|---|---|---|
| Runs in | A web browser | A terminal / PowerShell window |
| Needs Python on the viewer's computer | No (once deployed) | Yes |
| Charts | Interactive, with hover details | One PNG chart per run |
| Comparison with the previous run | Yes | Yes |
| Hour-by-hour table and CSV download | Yes | Yes (saved in `results/`) |

---

## 1. The web app

The web app is built with [Streamlit](https://streamlit.io). After it is deployed (section 3),
anyone with the link can use it in a browser: no Python, no terminal, no installation.

**What it shows**

* **Simulation settings** (sidebar): vehicle arrival rate, road capacity, simulation
  duration and initial queue, with their units and allowed ranges, and a **Run Simulation**
  button. A **demonstration scenario** list fills in the settings for each step of the
  suggested demonstration (section 5). The **fixed model rules**, which are not adjustable,
  are listed separately in the sidebar.
* **Results**: the outcome (for example *Queue growing* or *Queue cleared*) with its
  reason; metric cards for vehicles arriving, vehicles passing through, vehicles still
  waiting, longest queue, average waiting time and worst traffic condition; the two
  feedback effects; and the vehicle check.
* **Charts**: vehicles waiting in the queue over time; vehicles arriving vs road capacity
  each hour; and the traffic condition (demand ratio, Stable / Building / Severe) each hour.
  Hover over a chart to see the exact values.
* **Hourly results table**, with a CSV download (the same file the terminal program saves),
  and a PNG download of the chart for slides.
* **Compare with previous run**: after a second run, the two runs are shown side by side.
  The metric cards show the change from the previous run, and the queue chart draws the
  previous run as a dashed grey line.
* **How the model works**: variables, equations, feedback loops, assumptions, limitations
  and how to read the results, taken from `MODEL.md`.

Invalid settings are not simulated. The app shows the reason in plain words (for example
*"Please enter a number greater than 0 for the road capacity"*) and keeps the last valid
results on screen.

## 2. Run it on your own computer

You need **Python 3.10 or newer** ([python.org](https://www.python.org/downloads/)).
On Windows, tick **"Add python.exe to PATH"** during installation.

Open **PowerShell** in this folder. In File Explorer, open the project folder, click the
address bar, type `powershell`, and press Enter. Then install the libraries (once):

```powershell
py -m pip install -r requirements.txt
```

Start the web app:

```powershell
py -m streamlit run app.py
```

It opens in your browser at <http://localhost:8501>. Press **Ctrl+C** in PowerShell to stop it.
On macOS or Linux, use `python3` instead of `py`.

*(Optional)* To keep the libraries separate from other projects, create a virtual
environment first: `py -m venv .venv`, then `.venv\Scripts\activate` (Windows) or
`source .venv/bin/activate` (macOS/Linux), then run the two commands above. The `.venv`
folder is not uploaded to GitHub.

## 3. Put it online with Streamlit Community Cloud

Streamlit Community Cloud hosts the app for free and gives it a web address you can share.
The repository already contains everything it needs: the entry point **`app.py`** and the
libraries in **`requirements.txt`**. No secrets or API keys are used.

1. Go to **<https://share.streamlit.io/>**.
2. **Sign in**, using *Continue with GitHub*. If Streamlit asks to connect or authorize
   your GitHub account, allow it. Because `alyencs/road-runners-simulation` is a
   **private** repository, Streamlit must be allowed to access private repositories.
3. Click **Create app** (top right), then choose to deploy an app from GitHub
   (*"Yup, I have an app"*).
4. Fill in the form:
   * **Repository:** `alyencs/road-runners-simulation`
   * **Branch:** the branch that contains `app.py`. Use `main` after the changes are
     merged there, or the feature branch to try it before merging.
   * **Main file path:** `app.py`
   * **App URL** (optional): choose a short address, for example `road-runners`.
5. Open **Advanced settings** and choose **Python 3.12** (the version this project was
   tested with). The Python version cannot be changed later without deleting and
   redeploying the app. No secrets are needed. Save.
6. Click **Deploy**. The first build installs the libraries and takes a few minutes.
   When it finishes, the app opens at an address ending in `.streamlit.app`.
7. **Share it.** Copy the address from the browser. Apps deployed from a private
   repository are **private by default**, so only people you invite can open them. Click
   **Share** (top right of the app) and either invite your professor by email or, if
   you prefer, make the app public. Open the link in a private/incognito window to check
   what other people will see.

**Good to know**

* Every push to the deployed branch updates the app automatically within a minute or two.
* Apps that are not used for a while go to sleep. The first visitor sees a
  *"This app has gone to sleep"* page with a button to wake it up, which takes about a
  minute. **Open the link a few minutes before a presentation.**
* If the deployment fails, open **Manage app** (bottom right of the app page) to read the
  log. The most common cause is a wrong *Main file path*. It must be exactly `app.py`.

## 4. The terminal program (optional)

The original terminal version still works and uses the same model:

```powershell
py road_runners.py
```

On macOS or Linux, use `python3 road_runners.py`. It opens with a short description and
one settings screen:

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

* Type a setting's number (1–4) to change it. Pressing **Enter without typing** keeps the
  current value.
* Type **R** to run. The results appear immediately, and a chart window opens. Close the
  chart window to return to the settings.
* Change one setting and press **R** again. The new results are shown **next to the
  previous run**, and the chart draws the previous queue in grey.
* **T** prints the hour-by-hour table of the last run. **H** explains the model. **Q** quits.
* Every run saves its chart (`..._chart.png`) and hour-by-hour table (`..._hourly.csv`,
  which opens in Excel) in the `results` folder.

## 5. Settings, results and a suggested demonstration

| Setting | Allowed values | Meaning |
|---|---|---|
| Vehicle arrival rate | 0 – 1,000,000 vehicles/hour (decimals allowed) | Vehicles that want to use the road each hour |
| Road capacity | more than 0 – 1,000,000 vehicles/hour (decimals allowed) | The most vehicles the road can let through each hour |
| Simulation duration | 1 – 720 hours (whole number) | How many one-hour steps to simulate |
| Initial queue (vehicles already waiting) | 0 – 10,000,000 vehicles (whole number) | A queue that exists at the start, for example after an accident |

The starting values (1,100 / 1,000 / 12 / 0) are **examples**, not measured data. The upper
limits only reject values far beyond any single road.

| Result | Meaning |
|---|---|
| Vehicles arriving | Vehicles that joined the road during the simulation, after some drivers rerouted |
| Vehicles passing through | Vehicles that got through the bottleneck |
| Vehicles still waiting | The queue left when the simulation stops |
| Longest queue | The largest number of vehicles waiting at once |
| Average waiting time | Total time all vehicles spent in the queue ÷ number of vehicles (minutes) |
| Worst traffic condition | The most congested hour: Stable / Building / Severe, with Level of Service A–F |
| Drivers who took another route | Effect of the **rerouting** feedback (congestion makes some drivers avoid the road) |
| Capacity lost to spillback | Effect of the **spillback** feedback (severe queues reduce what the road can pass) |
| Outcome | Whether the queue never formed, cleared, is growing, is shrinking, is stable, or builds up and clears repeatedly, with the reason |
| Vehicle check | Waiting at start + arrived = passed + still waiting. It shows that no vehicle was lost or created |

**Suggested demonstration.** In the web app, pick each step from *Load a demonstration
scenario*, then press **Run Simulation**. Each run is compared with the one before it.

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

The 52 automated tests check:

* **Model** (`tests/test_model.py`): the equations against hand calculations, vehicle
  conservation on 500 random inputs, the queue verdicts, the results quoted in this
  README and `MODEL.md`, input validation, and the terminal program (including that its
  chart and saved table contain exactly the simulated values).
* **Web helpers** (`tests/test_web.py`): input checking, and that every table, CSV
  download and chart uses the model's actual output.
* **Web app** (`tests/test_app.py`): runs `app.py` without a browser, using Streamlit's
  test runner. It covers the default run, several other settings, an invalid input, the
  comparison with the previous run, the demonstration scenarios and the reset button.

The web tests are skipped automatically if Streamlit is not installed.

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `No module named 'streamlit'` (or `matplotlib`) | Run `py -m pip install -r requirements.txt` in this folder. |
| `py` or `python` is not recognised | Install Python from python.org with "Add python.exe to PATH" ticked, then open a new PowerShell window. |
| `No module named 'roadrunners'` | Run the command from inside the project folder (the one containing `app.py`). |
| The web app does not open in the browser | Open <http://localhost:8501> yourself while `streamlit run` is still running. |
| The online app shows "This app has gone to sleep" | Click the button to wake it up and wait about a minute. |
| The terminal program seems to stop after a run | A chart window is open (it may be behind other windows). Close it to continue. |

## 8. Files

```
road-runners-simulation/
├── app.py                 the web app (Streamlit entry point)
├── road_runners.py        the terminal program
├── requirements.txt       libraries: streamlit, altair, pandas, matplotlib, numpy
├── README.md              this file
├── MODEL.md               the model: variables, equations, assumptions, limitations
├── roadrunners/
│   ├── model.py           the simulation model (all equations)
│   ├── interface.py       terminal screens, input checking, results rows, CSV
│   ├── charts.py          the results chart (PNG) used by both versions
│   └── web.py             tables and interactive charts for the web app
└── tests/
    ├── test_model.py      model and terminal program
    ├── test_web.py        web helpers
    └── test_app.py        the web app itself
```
