# European Energy System Optimization Model

A PyPSA-based linear capacity expansion and dispatch optimization model for the European electricity and heat sector. The model is used to study optimal technology mixes, cross-border transmission, CO₂ constraints, and sector coupling across multiple scenarios.

---

## Overview

This project builds and solves least-cost energy system optimization problems using [PyPSA](https://pypsa.org/). Electricity demand and renewable capacity factor time series are sourced from the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/), and technology cost data is taken from the [Fraunhofer ISE](https://www.ise.fraunhofer.de/) cost database. Results are exported to JSON and visualized as publication-ready figures.

The model covers:

- Single-country and multi-country setups (Belgium, France, Netherlands, Germany/Luxembourg)
- Dispatchable and volatile renewable generators
- Battery and pumped-storage hydro storage
- AC electricity transmission lines and CH₄ gas pipelines
- Sector coupling (heat demand, heat pumps, gas boilers, CHP)
- Global CO₂ emission constraints with shadow price extraction
- Sensitivity analysis across weather years and CO₂ reduction levels

---

## Project Structure

```
.
├── main.py                         # Entry point — defines configs and runs all tasks
├── src/
│   ├── input.py                    # InputHandler: fetches and caches ENTSO-E data
│   ├── networkbuilder.py           # NetworkBuilder: builds and optimizes PyPSA networks
│   ├── visualizer.py               # Visualizer: generates all result plots
│   └── results_export.py           # Exports results to structured JSON files
├── technology_costs/
│   └── costs_2025.csv              # Fraunhofer ISE technology cost data
├── entsoe_data/                    # Local cache for ENTSO-E load and capacity factor CSVs
└── results/
    ├── figures/                    # Output plots (one subfolder per scenario)
    └── numerical_results/          # Output JSON files (one per scenario)
```

---

## Installation

**Python 3.10+ is recommended.**

Install dependencies:

```bash
pip install pypsa entsoe-py pandas numpy matplotlib
```

You will also need a working linear solver. PyPSA supports [HiGHS](https://highs.dev/) (open-source, recommended), GLPK, Gurobi, and others. HiGHS is installed automatically with `highspy`:

```bash
pip install highspy
```

---

## Configuration

All scenarios are defined as configuration dictionaries at the top of `main.py`. The following keys are supported:

| Key | Type | Description |
|---|---|---|
| `countries` | `list[str]` | ENTSO-E country codes to model (e.g. `["BE", "FR"]`) |
| `years` | `list[int]` | Simulation years (e.g. `[2023]`) |
| `technologies_disp` | `list[str]` | Dispatchable technologies to include |
| `technologies_vol` | `list[str]` | Volatile (renewable) technologies to include |
| `technologies_storage` | `list[str]` | Storage technologies (optional) |
| `voltage_level` | `int` | Nominal voltage in kV (e.g. `400`) |
| `reactance` | `float` | Line reactance in p.u. (e.g. `0.1`) |
| `transmission_lines` | `list[dict]` | AC line definitions (multi-country only) |
| `CH4_lines` | `list[dict]` | Methane pipeline definitions (optional) |
| `global_CO2_limit` | `float` | Annual CO₂ cap in tonnes (optional) |
| `include_heat` | `bool` | Enable heat sector coupling (optional) |
| `no_gas_supply` | `bool` | Remove CH₄ availability entirely (optional) |
| `load_year` | `int` | Fix demand to a specific year (used in weather-year sensitivity) |

---

## Scenarios

The following scenarios are defined in `main.py` and solved sequentially:

| Scenario | Description |
|---|---|
| **A** | Single-country baseline for Belgium (2023) |
| **B** | Weather-year sensitivity — Belgium optimized across 2020–2024 with fixed 2023 demand |
| **C** | Adds pumped-storage hydro to scenario A |
| **D** | Multi-country model: Belgium, France, Netherlands, Germany/Luxembourg with AC lines |
| **F** | CO₂ sensitivity — sweeps CO₂ limit from 100% down to 0% of 1990 reference level |
| **G** | Multi-country with CH₄ pipeline network (NL as gas import hub) |
| **H** | Scenario G with a binding CO₂ constraint (−55% vs. 1990) |
| **I** | Scenario H with heat sector coupling (heat pumps, gas boilers, CHP) |
| **J** | Scenario I with zero gas supply — forces full decarbonization of heat and power |

---

## Running the Model

```bash
python main.py
```

On first run, ENTSO-E data will be fetched via API and cached in `entsoe_data/`. Subsequent runs load from cache. The ENTSO-E API key is set in `src/input.py` — replace it with your own key if needed (free registration at [transparency.entsoe.eu](https://transparency.entsoe.eu/)).

Results are written to:
- `results/figures/<scenario>/` — PNG plots
- `results/numerical_results/<scenario>.json` — structured JSON output

---

## Input Data

### Electricity Load and Capacity Factors (`src/input.py`)

`InputHandler` connects to the ENTSO-E API to retrieve:

- **Electricity load** — hourly actual load per country and year
- **Capacity factors** — computed as actual generation divided by installed capacity for solar, onshore wind, and offshore wind
- **Heat load** — read from local CSV files produced by the [when2heat project](https://when2heat.eu/)

All data is cached locally in `entsoe_data/` as CSV files to avoid repeated API calls.

### Technology Costs (`technology_costs/costs_2025.csv`)

Indexed by `(technology, parameter)`. Parameters used include:

- `investment` — overnight capital cost (€/kW)
- `FOM` — fixed O&M as a percentage of investment
- `efficiency` — conversion efficiency
- `lifetime` — economic lifetime in years
- `fuel` — fuel cost (€/MWh)
- `CO2 intensity` — specific emissions (t CO₂/MWh fuel)

---

## Outputs

### Figures (`src/visualizer.py`)

The `Visualizer` class produces the following plots depending on the scenario:

| Method | Description |
|---|---|
| `plot_dispatch_time_series` | Stacked area chart of hourly generation dispatch |
| `plot_annual_electricity_mix` | Bar chart of annual electricity generation by technology |
| `plot_installed_capacity` | Optimal installed capacity by technology and country |
| `plot_load_duration_curve` | Sorted load duration curve |
| `plot_storage_behavior` | Storage charge/discharge and state of charge over time |
| `plot_sensitivity_capacity_to_weather_years` | Capacity sensitivity across weather years |
| `plot_capacity_factors` | Seasonal capacity factor profiles |
| `plot_line_utilisation_bar` | Transmission line utilization rates |
| `plot_network_diagram` | Geographic network diagram with power flows |
| `plot_dual_network_diagram` | Dual electricity + gas network diagram |
| `plot_energy_transport_comparison` | Transported energy by carrier |
| `plot_scenario_comparison` | Side-by-side capacity/generation comparison between scenarios |
| `plot_co2_sensitivity` | System cost and CO₂ shadow price vs. CO₂ limit |
| `plot_annual_final_energy_mix` | Final energy by carrier (sector-coupled scenarios) |
| `plot_energy_demand_split` | Split of energy demand by sector |
| `plot_dispatch_diff_time_series` | Dispatch difference relative to a reference scenario |

### JSON Results (`src/results_export.py`)

`export_results_to_json` writes a structured JSON file per scenario containing:

- `objective_value` — total system cost (€/year) by year
- `transported_energy_TWh` — electricity and CH₄ transport volumes by year
- `co2_shadow_price_EUR_per_tCO2` — marginal cost of CO₂ constraint (if active)
- Per-country blocks (e.g. `2023_BE`) with:
  - `annual_dispatch_TWh` — annual generation by technology
  - `installed_capacity_GW` — optimal installed capacity by technology

Results are accumulated across years within the same file, so multi-year scenarios append to a single output file.

---

## Notes

- The model uses a **7% real discount rate** for all investment decisions.
- In multi-country gas scenarios, **the Netherlands acts as the sole CH₄ import hub** — all other countries must import gas via the pipeline network.
- The CO₂ constraint is implemented as a **custom PyPSA constraint** over all links and generators, with the dual variable extracted post-optimization to yield the shadow price.
- Capacity factors are clipped to [0, 1] and set to zero where installed capacity data is missing.
