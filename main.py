import copy
import json
import os

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import numpy as np

from src.input import InputHandler
from src.networkbuilder import NetworkBuilder
from src.visualizer import Visualizer
from src.results_export import export_results_to_json

""">>>> SPECIFY CONFIGURATION-DICTIONARIES FOR EACH TASK <<<<"""
CONFIG_A = {
    "countries": ["BE"],    # must be the same naming convention as used by ENTSO-E
    "years": [2023],   # data in good quality available from ENTSO-E for 2015-2024
    "technologies_disp": ["biomass CHP", "CCGT", "coal", "gas boiler steam", "industrial heat pump high temperature", "nuclear", "OCGT"],  # must be the same naming convention as in cost list
    "technologies_vol": ["offwind", "onwind", "solar"],   # must be the same naming convention as in cost list
    'voltage_level': 400, # kV, specified by assignment guidelines
    'reactance': 0.1 # specified by assignment guidelines`
}

CONFIG_B = copy.deepcopy(CONFIG_A)
CONFIG_B["years"] = [2020, 2021, 2022, 2023, 2024]
CONFIG_B["load_year"] = 2023

CONFIG_C = copy.deepcopy(CONFIG_A)
CONFIG_C["technologies_storage"] = ["Pumped-Storage-Hydro-bicharger"]

CONFIG_D = copy.deepcopy(CONFIG_A)
CONFIG_D["countries"] = ["BE", "FR", "NL", "DE_LU"]    # must be the same naming convention as used by ENTSO-E

CONFIG_D ["transmission_lines"] = [
    {"name": "BE-FR",    "bus0": "BE",    "bus1": "FR",    "x": 0.1, "s_nom": 6000},
    {"name": "BE-NL",    "bus0": "BE",    "bus1": "NL",    "x": 0.1, "s_nom": 6070},
    {"name": "BE-DE_LU", "bus0": "BE",    "bus1": "DE_LU", "x": 0.1, "s_nom": 1000},
    {"name": "FR-DE_LU", "bus0": "FR",    "bus1": "DE_LU", "x": 0.1, "s_nom": 9000},
    {"name": "NL-DE_LU", "bus0": "NL",    "bus1": "DE_LU", "x": 0.1, "s_nom": 5500},
]

CONFIG_F = copy.deepcopy(CONFIG_C)
CONFIG_F["global_CO2_limit"] = 103911000   # t CO2-eq, emissions from energy sector 1990

CONFIG_G = copy.deepcopy(CONFIG_D)
CONFIG_G["CH4_lines"] = [
    {"name": "BE-FR",    "bus0": "BE",    "bus1": "FR"},
    {"name": "BE-NL",    "bus0": "BE",    "bus1": "NL"},
    {"name": "BE-DE_LU", "bus0": "BE",    "bus1": "DE_LU"},
    {"name": "FR-DE_LU", "bus0": "FR",    "bus1": "DE_LU"},
    {"name": "NL-DE_LU", "bus0": "NL",    "bus1": "DE_LU"},
]
CONFIG_H = copy.deepcopy(CONFIG_G)
CONFIG_H["global_CO2_limit"] = 623785500   # t CO2-eq, based on emissions from energy sector in 1990 and assuming a 55% reduction in 2025 (the goal for 2030 that is reached sooner for the energy sector) 

CONFIG_I = copy.deepcopy(CONFIG_H)
CONFIG_I["include_heat"] = True

CONFIG_J = copy.deepcopy(CONFIG_I)

""">>>> SOLVE THE OPTIMIZATION PROBLEMS<<<<"""
# # TASK A
# input_data_a = InputHandler(CONFIG_A)
# network_a = NetworkBuilder(CONFIG_A, input_data_a, CONFIG_A["years"][0])
# visualizer_a = Visualizer(network_a.network, scenario_name = 'a')
# visualizer_a.plot_dispatch_time_series(pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01"))
# visualizer_a.plot_annual_electricity_mix()
# visualizer_a.plot_installed_capacity()
# visualizer_a.plot_load_duration_curve()

# export_results_to_json(network_a.network, "task_a", CONFIG_A["years"][0]) 

# # TASK B
# input_data_b = InputHandler(CONFIG_B)
# networks = {}
# capacity_by_tech = {} # CHANGE: added capacity per year for the plot of each technology

# for year in CONFIG_B["years"]:
#     network_b = NetworkBuilder(CONFIG_B, input_data_b, year)
#     networks[year] = network_b

#     export_results_to_json(
#         network_b.network,
#         "task_b",
#         year
#     )

#     # --- GENERATORS (solar, wind, coal, nuclear)
#     for gen in network_b.network.generators.index:
#         cap = network_b.network.generators.loc[gen, "p_nom_opt"]
#         capacity_by_tech.setdefault(gen, []).append(cap)

#     # --- LINKS (CCGT, OCGT, CHP, etc)
#     for link in network_b.network.links.index:
#         cap = network_b.network.links.loc[link, "p_nom_opt"]
#         capacity_by_tech.setdefault(link, []).append(cap)

# print("\nCAPACITY_BY_TECH")
# for tech, vals in capacity_by_tech.items():
#     print(tech, vals)

# visualizer_b = Visualizer(networks[CONFIG_B["years"][0]].network, scenario_name="b")
# visualizer_b.capacity_dict = capacity_by_tech
# visualizer_b.plot_sensitivity_capacity_to_weather_years()
# visualizer_cf = Visualizer(networks[CONFIG_B["years"][0]].network, scenario_name="b")
# visualizer_cf.plot_capacity_factors(input_data_b)

# TASK C
input_data_c = InputHandler(CONFIG_C)
network_c = NetworkBuilder(CONFIG_C, input_data_c, CONFIG_C["years"][0])
# visualizer_c = Visualizer(network_c.network, scenario_name = 'c')
# visualizer_c.plot_dispatch_time_series(pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01"))
# visualizer_c.plot_dispatch_diff_time_series(
#     other=visualizer_a,
#     start_summer=pd.Timestamp("2023-07-01"),
#     start_winter=pd.Timestamp("2023-12-01"),
# )
# visualizer_c.plot_annual_electricity_mix()
# visualizer_c.plot_storage_behavior(
#     start_summer=pd.Timestamp("2023-07-01"),
#     start_winter=pd.Timestamp("2023-12-01"),
# )
# visualizer_c.plot_installed_capacity()

# export_results_to_json(network_c.network, "task_c", CONFIG_C["years"][0])

# # TASK D
# input_data_d = InputHandler(CONFIG_D)
# network_d = NetworkBuilder(CONFIG_D, input_data_d, CONFIG_D["years"][0])
# visualizer_d = Visualizer(network_d.network, scenario_name = 'd')
# visualizer_d.plot_annual_electricity_mix()
# visualizer_d.plot_installed_capacity()
# visualizer_d.plot_line_utilisation_bar()
# visualizer_d.plot_network_diagram()

# export_results_to_json(network_d.network, "task_d", CONFIG_D["years"][0])

# TASK F
input_data_f = InputHandler(CONFIG_F)
REF_CO2 = CONFIG_F["global_CO2_limit"]

networks_f = {}
for percent in np.arange(1, 0, -0.1):
    co2_limit = percent * REF_CO2
    CONFIG_F["global_CO2_limit"] = co2_limit
    network_f = NetworkBuilder(CONFIG_F, input_data_f, CONFIG_F["years"][0])
    networks_f[round(percent, 2)] = network_f

    n = network_f.network

    print("\nCO2 TEST")
    print("percent:", round(percent, 2))
    print("cap:", co2_limit)
    print("objective:", n.objective)

    if "CO2Limit" in n.model.constraints:
        dual = n.model.constraints["CO2Limit"].dual
        print("CO2 shadow price / mu:", dual)
    else:
        print("CO2Limit NOT FOUND in model constraints")

results_f = {}

for percent, net in networks_f.items():
    n = net.network

    results_f[percent] = {
        "objective": n.objective,
        "co2_shadow_price": abs(n.model.constraints["CO2Limit"].dual.item())
    }

os.makedirs("results/numerical_results", exist_ok=True)
with open("results_task_f.json", "w") as f:
    json.dump(results_f, f, indent=4)

# grouped bar chart: C vs F at 100%
visualizer_c = Visualizer(network_c.network, scenario_name="c")
visualizer_f = Visualizer(networks_f[max(networks_f.keys())].network, scenario_name="f")
visualizer_f.plot_scenario_comparison(
    other=visualizer_c,
    self_label="C (no CO₂ limit)",
    other_label="F (1990 CO₂ limit)",
    name="comparison_c_vs_f",
)
# sensitivity plot
visualizer_f.plot_co2_sensitivity(
    networks_f=networks_f,
    ref_co2=REF_CO2,
    name="co2_sensitivity",
)

# # TASK G
# input_data_g = InputHandler(CONFIG_G)
# network_g = NetworkBuilder(CONFIG_G, input_data_g, CONFIG_G["years"][0])
# visualizer_g = Visualizer(network_g.network, scenario_name="g")
# visualizer_g.plot_dual_network_diagram()
# energy_transport_table = visualizer_g.plot_energy_transport_comparison()
# print(energy_transport_table)

# export_results_to_json(network_g.network, "task_g", CONFIG_G["years"][0])

# # TASK H
# input_data_h = InputHandler(CONFIG_H)
# network_h = NetworkBuilder(CONFIG_H, input_data_h, CONFIG_H["years"][0])

# # CO2 shadow price
# co2_shadow_price = abs(network_h.network.model.constraints["CO2Limit"].dual.item())
# print(f"CO2 shadow price for task H: {co2_shadow_price:.2f} €/tCO2")

# export_results_to_json(network_h.network, "task_h", CONFIG_H["years"][0])

# # TASK i
# input_data_i = InputHandler(CONFIG_I)
# network_i = NetworkBuilder(CONFIG_I, input_data_i, CONFIG_I["years"][0])

# export_results_to_json(network_i.network, "task_i", CONFIG_I["years"][0])

# # TASK J
# input_data_j = InputHandler(CONFIG_J)
# network_j = NetworkBuilder(CONFIG_J, input_data_j, CONFIG_J["years"][0])

# export_results_to_json(network_j.network, "task_j", CONFIG_J["years"][0])

print('all network optimizations were successful')