import json
import os
import numpy as np


def _clean(x, decimals=4):
    if x is None:
        return None
    if isinstance(x, (np.integer, np.floating, int, float)):
        x = round(float(x), decimals)
        if abs(x) < 1e-6:
            return 0.0
        return x
    return x


def simplify_name(name):
    parts = name.split("_")

    try:
        type_idx = next(i for i, p in enumerate(parts) if p in ("disp", "vol", "storage"))
        country = parts[type_idx + 1]
        tech = "_".join(parts[type_idx + 2:])
    except StopIteration:
        return None, name

    return country, tech


def export_results_to_json(network, scenario_name, year, path=None):
    if path is None:
        os.makedirs("results/numerical_results", exist_ok=True)
        path = f"results/numerical_results/{scenario_name}.json"
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    year = str(year)

    results = {
        "objective_value": _clean(network.objective),
        "transported_energy_TWh": {},
    }

    if "CO2Limit" in network.global_constraints.index:
        results["co2_shadow_price_EUR_per_tCO2"] = _clean(
            abs(network.global_constraints.loc["CO2Limit", "mu"])
        )

    # generators: coal, nuclear, solar, wind, etc.
    for gen in network.generators.index:
        country, tech = simplify_name(gen)
        key = f"{year}_{country}"

        if key not in results:
            results[key] = {
                "annual_dispatch_TWh": {},
                "installed_capacity_GW": {},
            }

        dispatch_twh = network.generators_t.p[gen].sum() / 1e6
        capacity_gw = network.generators.loc[gen, "p_nom_opt"] / 1000

        results[key]["annual_dispatch_TWh"][tech] = _clean(dispatch_twh)
        results[key]["installed_capacity_GW"][tech] = _clean(capacity_gw)

    # links: CCGT, OCGT, CHP, gas boiler, heat pump
    for link in network.links.index:
        if link.startswith("CH4_"):
            continue

        country, tech = simplify_name(link)
        key = f"{year}_{country}"

        if key not in results:
            results[key] = {
                "annual_dispatch_TWh": {},
                "installed_capacity_GW": {},
            }

        capacity_gw = network.links.loc[link, "p_nom_opt"] / 1000

        if link in network.links_t.p1.columns:
            dispatch_twh = (-network.links_t.p1[link]).clip(lower=0).sum() / 1e6
        else:
            dispatch_twh = 0.0

        results[key]["annual_dispatch_TWh"][tech] = _clean(dispatch_twh)
        results[key]["installed_capacity_GW"][tech] = _clean(capacity_gw)

    # storage
    for storage in network.storage_units.index:
        country, tech = simplify_name(storage)
        key = f"{year}_{country}"

        if key not in results:
            results[key] = {
                "annual_dispatch_TWh": {},
                "installed_capacity_GW": {},
            }

        capacity_gw = network.storage_units.loc[storage, "p_nom_opt"] / 1000
        dispatch_twh = network.storage_units_t.p[storage].clip(lower=0).sum() / 1e6

        results[key]["annual_dispatch_TWh"][tech] = _clean(dispatch_twh)
        results[key]["installed_capacity_GW"][tech] = _clean(capacity_gw)

    # heat demand (opcional)
    if "heat" in [carrier for carrier in network.carriers.index]:
        for load in network.loads.index:
            if "_heat" in load:
                country = load.split("_")[1]
                key = f"{year}_{country}"

                if key not in results:
                    results[key] = {
                        "annual_dispatch_TWh": {},
                        "installed_capacity_GW": {},
                    }

                heat_demand = network.loads_t.p_set[load].sum() / 1e6
                results[key]["annual_dispatch_TWh"]["heat_demand"] = _clean(heat_demand)

    # electricity transport
    if not network.lines.empty:
        results["transported_energy_TWh"]["electricity"] = _clean(
            network.lines_t.p0.abs().sum().sum() / 1e6
        )

    # CH4 transport
    ch4_links = [link for link in network.links.index if link.startswith("CH4_")]
    if ch4_links:
        results["transported_energy_TWh"]["CH4"] = _clean(
            network.links_t.p0[ch4_links].abs().sum().sum() / 1e6
        )

        # If file exists, load previous years/tasks
    if os.path.exists(path):
        with open(path, "r") as f:
            existing_results = json.load(f)
    else:
        existing_results = {
            "objective_value": {},
            "transported_energy_TWh": {},
            "co2_shadow_price_EUR_per_tCO2": {},
        }

    # Save objective by year
    existing_results["objective_value"][year] = results["objective_value"]

    if "co2_shadow_price_EUR_per_tCO2" in results:
        existing_results["co2_shadow_price_EUR_per_tCO2"][year] = results["co2_shadow_price_EUR_per_tCO2"]

    # Save transported energy by year
    existing_results["transported_energy_TWh"][year] = results["transported_energy_TWh"]

    # Save country-year blocks, e.g. 2020_BE, 2021_BE
    for key, value in results.items():
        if key not in ["objective_value","transported_energy_TWh","co2_shadow_price_EUR_per_tCO2",]:
            existing_results[key] = value

    with open(path, "w") as f:
        json.dump(existing_results, f, indent=4)

    return existing_results