# ROAD RUNNERS: Traffic Flow Simulation

**The Impact of Vehicle Arrival Rate and Road Capacity on Traffic Flow**

A System Dynamics simulation of one road bottleneck, made for the final project in
Introduction to Modeling and Simulation (6IMODSIM), Holy Angel University.

Each simulated hour, vehicles **arrive** and the road lets through at most its **capacity**.
Vehicles that cannot pass **wait in a queue** and carry over to the next hour. Congestion
feeds back on itself: some drivers **reroute**, and severe queues **spill back** and reduce
the capacity. The simulation shows whether a queue forms, how long it gets and how long
drivers wait. The model, its equations, feedback loops, assumptions and limitations are
explained in **[MODEL.md](MODEL.md)**.

The simulation runs as a **web app** (Streamlit, deployed on Streamlit Community Cloud) and
as an optional **terminal program**. Both use the same model.

## Project files

| File | Purpose |
|---|---|
| `app.py` | The web app: the page layout. This is the file Streamlit Community Cloud runs. |
| `roadrunners/model.py` | The simulation model: every equation, rule and result. |
| `roadrunners/interface.py` | The input limits and error messages, the result texts and CSV file shared by both versions, and the terminal program's menu. |
| `roadrunners/web.py` | Metric cards, tables and interactive charts for the web app. |
| `roadrunners/charts.py` | The two-panel results chart (terminal chart window and the web app's PNG download). |
| `road_runners.py` | Starts the terminal program. |
| `tests/` | Automated tests (see [Tests](#tests)). |
| `requirements.txt` | The Python libraries needed: streamlit, altair, pandas, matplotlib, numpy. |
| `MODEL.md` | The model documentation. |

## Run it on your own computer

You need **Python 3.10 or newer** ([python.org](https://www.python.org/downloads/)). On Windows,
tick **"Add python.exe to PATH"** during installation. Open PowerShell in the project folder
(in File Explorer, click the address bar, type `powershell` and press Enter), then:

```powershell
py -m pip install -r requirements.txt     # once
py -m streamlit run app.py                # the web app, opens at http://localhost:8501
py road_runners.py                        # or: the terminal program
```

On macOS or Linux, use `python3` instead of `py`. Stop the web app with **Ctrl+C**.
*(Optional: install into a virtual environment, `py -m venv .venv`, to keep the libraries
separate from other projects. The `.venv` folder is not uploaded to GitHub.)*

## How to use it

1. In the sidebar, set the four inputs, or keep the example values:

   | Setting | Allowed values | Meaning |
   |---|---|---|
   | Vehicle arrival rate | 0 – 1,000,000 vehicles/hour | Vehicles that want to use the road each hour |
   | Road capacity | more than 0 – 1,000,000 vehicles/hour | The most vehicles the road can let through each hour |
   | Simulation duration | 1 – 720 hours (whole number) | How many one-hour steps to simulate |
   | Initial queue | 0 – 10,000,000 vehicles (whole number) | Vehicles already waiting at the start, for example after an accident |

   The example values (1,100 / 1,000 / 12 / 0) are illustrative, not measured data. The
   rerouting and spillback rules are fixed parts of the model and are listed under
   *Fixed model rules* in the sidebar.
2. Press **Run Simulation**. A setting outside its allowed range is not simulated: the app
   explains what is wrong and keeps the last valid results on screen.
3. Change one setting and press **Run Simulation** again. The new run is compared with the
   previous one in the metric cards, the queue chart (previous run as a dashed grey line)
   and the **Compare with previous run** tab.

The terminal program works the same way: type a setting's number (1–4) to change it,
**R** to run, **T** for the hour-by-hour table, **H** for help and **Q** to quit. It saves
each run's chart and table in a `results` folder.

**Suggested demonstration.** In the web app, pick each step from *Load a demonstration
scenario*, then press **Run Simulation**.

| Step | Settings (arrival / capacity / initial queue) | What happens |
|---|---|---|
| 1 | 1,100 / 1,000 / 0 | Arrivals exceed capacity, so the queue **grows** every hour (505 vehicles after 12 h) |
| 2 | 1,100 / **1,200** / 0 | The road can pass everyone: **no queue**. Capacity decides whether a queue forms |
| 3 | **1,040** / 1,000 / 0 | The queue **builds up and clears repeatedly**: rerouting drivers keep it in check |
| 4 | **800** / 1,000 / **500** | An existing queue **clears** within 3 hours once arrivals are below capacity |
| 5 | **1,300** / 1,000 / 0 | A 30 % overload: **2,640** vehicles waiting after 12 h instead of 505 |

## Reading the results

* **Outcome**: whether the queue never formed, cleared, is growing, is shrinking, is stable,
  or builds up and clears repeatedly, with the reason.
* **Metric cards**: vehicles arriving, passing through and still waiting, the longest
  queue, the average waiting time, the worst traffic condition, and the effect of each
  feedback loop. The **vehicle check** confirms that no vehicle was lost or created.
* **Vehicles waiting in the queue**: the main result. Is the queue growing, stable or clearing?
* **Vehicles arriving vs road capacity**: vehicles per hour, one step per hour. The queue
  grows in every hour where arrivals are above capacity. Dashed lines show the original
  settings when rerouting or spillback changed them.
* **Traffic condition each hour**: the demand ratio, (queue + arrivals) ÷ capacity,
  coloured Stable / Building / Severe. It decides the feedback in the next hour.
* **Hourly results table**: every value of every hour, downloadable as CSV. The chart can be
  downloaded as a PNG for slides.

Each measure is defined in [MODEL.md → How to read the results](MODEL.md#how-to-read-the-results).

## Tests

```powershell
py -m unittest discover -s tests -v
```

| File | What it checks |
|---|---|
| `tests/test_model.py` | The equations against hand calculations, vehicle conservation on 500 random inputs, the feedback loops, the queue verdicts, the results quoted in the documentation, input checking, and a full terminal session |
| `tests/test_web.py` | That every table, metric, CSV download and chart in the web app is the model's actual output |
| `tests/test_app.py` | Runs `app.py` without a browser: default and other settings, an invalid input, the run comparison, the scenarios and the reset button |

The web tests are skipped automatically if Streamlit is not installed.

## Deploying on Streamlit Community Cloud

The app is deployed from the **`main`** branch with `app.py` as its main file.
`requirements.txt` lists everything it needs, and it uses no secrets or API keys.

**Updating the live app.** Every change merged into `main` is picked up automatically within
a minute or two. Work on another branch does not affect the live app until it is merged.
If an update fails, open **Manage app** (bottom right of the app) to read the log.

**Deploying it again from scratch** (for example in another account):

1. Go to <https://share.streamlit.io/> and sign in with GitHub. Allow Streamlit to access
   the repository. If it is private, Streamlit must be allowed to read private repositories.
2. Click **Create app** → deploy from GitHub. Choose repository
   `alyencs/road-runners-simulation`, branch `main`, main file path `app.py`.
3. Under **Advanced settings**, choose **Python 3.12**. It cannot be changed later without
   redeploying. Click **Deploy**. The first build takes a few minutes.
4. Copy the `.streamlit.app` address. Use **Share** in the app to control who can open it,
   and check the link in a private/incognito window.

Apps that have not been used for a while go to sleep. The first visitor sees a button to
wake the app, which takes about a minute, so open the link a few minutes before a presentation.

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named 'streamlit'` (or `matplotlib`) | Run `py -m pip install -r requirements.txt` in the project folder. |
| `py` or `python` is not recognised | Install Python with "Add python.exe to PATH" ticked, then open a new PowerShell window. |
| `No module named 'roadrunners'` | Run the command from the project folder (the one containing `app.py`). |
| The terminal program seems to stop after a run | A chart window is open, possibly behind other windows. Close it to continue. |
