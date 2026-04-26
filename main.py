import matplotlib
matplotlib.use("Agg")  # non-interactive backend, no Qt needed
import copy

import pandas as pd
import numpy as np

from src.input import InputHandler
from src.networkbuilder import NetworkBuilder
from src.visualizer import Visualizer

""">>>> SPECIFY CONFIGURATION-DICTIONARIES FOR EACH TASK <<<<"""
CONFIG_A = {
    "countries": ["BE"],    # must be the same naming convention as used by ENTSO-E
    "years": [2023],   # data in good quality available from ENTSO-E for 2015-2024
    "technologies_conv": {"BE": ["CCGT", "nuclear", 'biomass CHP']},  # must be the same naming convention as in cost list
    "technologies_vol": {"BE": ["solar-utility", "onwind", "offwind"]},
    'voltage_level': 400, # kV, specified by assignment guidelines
    'reactance': 0.1 # specified by assignment guidelines`
}

CONFIG_B = copy.deepcopy(CONFIG_A)
CONFIG_B["years"] = [2020, 2021, 2022, 2023, 2024]

CONFIG_C = copy.deepcopy(CONFIG_A)
CONFIG_C["technologies_storage"] = ["Pumped-Storage-Hydro-bicharger"]

CONFIG_D = copy.deepcopy(CONFIG_A)
CONFIG_D["countries"] = ["BE", "FR", "NL", "DE_LU"]    # must be the same naming convention as used by ENTSO-E
CONFIG_D["technologies_conv"]["FR"] = ["nuclear", "CCGT", "biomass CHP"]    # TODO adjust based on real technology mix
CONFIG_D["technologies_vol"]["FR"] = ["onwind", "solar-utility", "hydro"] # TODO adjust based on real technology mix
CONFIG_D["technologies_conv"]["NL"] = ["CCGT", "coal", "oil", "biomass CHP"]    # TODO adjust based on real technology mix
CONFIG_D["technologies_vol"]["NL"] = ["onwind", "offwind", "solar-utility"] # TODO adjust based on real technology mix
CONFIG_D["technologies_conv"]["DE_LU"] = ["CCGT", "coal", "oil", "biomass CHP"] # TODO adjust based on real technology mix
CONFIG_D["technologies_vol"]["DE_LU"] = ["onwind", "offwind", "solar-utility"]  # TODO adjust based on real technology mix

CONFIG_D ["transmission_lines"] = [
    {"name": "BE-FR",    "bus0": "BE",    "bus1": "FR",    "x": 0.1, "s_nom": 1850},
    {"name": "BE-NL",    "bus0": "BE",    "bus1": "NL",    "x": 0.1, "s_nom": 950},
    {"name": "BE-DE_LU", "bus0": "BE",    "bus1": "DE_LU", "x": 0.1, "s_nom": 400},
    {"name": "FR-DE_LU", "bus0": "FR",    "bus1": "DE_LU", "x": 0.1, "s_nom": 3000},
    {"name": "NL-DE_LU", "bus0": "NL",    "bus1": "DE_LU", "x": 0.1, "s_nom": 3500},
]

CONFIG_F = copy.deepcopy(CONFIG_C)
CONFIG_F["global_CO2_limit"] = 103911   # Gg CO2-eq, emissions from energy sector 1990 

CONFIG_G = copy.deepcopy(CONFIG_D)
CONFIG_G["CH4_lines"] = [
    {"name": "BE-FR",    "bus0": "BE",    "bus1": "FR"},
    {"name": "BE-NL",    "bus0": "BE",    "bus1": "NL"},
    {"name": "BE-DE_LU", "bus0": "BE",    "bus1": "DE_LU"},
    {"name": "FR-DE_LU", "bus0": "FR",    "bus1": "DE_LU"},
    {"name": "NL-DE_LU", "bus0": "NL",    "bus1": "DE_LU"},
]
CONFIG_H = copy.deepcopy(CONFIG_G)
CONFIG_H["global_CO2_limit"] = 623785.5   # Gg CO2-eq, based on emissions from energy sector in 1990 and assuming a 55% reduction in 2025 (the goal for 2030 that is reached sooner for the energy sector) 

CONFIG_I = copy.deepcopy(CONFIG_H)
CONFIG_I["include_heat"] = True

CONFIG_J = copy.deepcopy(CONFIG_I)

""">>>> SOLVE THE OPTIMIZATION PROBLEMS<<<<"""
# TASK A
input_data_a = InputHandler(CONFIG_A)
network_a = NetworkBuilder(CONFIG_A, input_data_a, CONFIG_A["years"][0])
visualizer_a = Visualizer(network_a.network, scenario_name = 'a')
visualizer_a.plot_dispatch_time_series(pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01"))
visualizer_a.plot_annual_electricity_mix()
visualizer_a.plot_installed_capacity()

# TASK B
input_data_b = InputHandler(CONFIG_B)
networks = {}
capacity_by_tech = {} # CHANGE: added capacity per year for the plot of each technology

for year in CONFIG_B["years"]:
    network_b = NetworkBuilder(CONFIG_B, input_data_b, year)
    networks[year] = network_b
    for gen in network_b.network.generators.index: # CHANGE: loop through generators to get capacity per technology for each year
        cap = network_b.network.generators.loc[gen, "p_nom_opt"]
        if gen not in capacity_by_tech:
            capacity_by_tech[gen] = []
        capacity_by_tech[gen].append(cap)

visualizer_b = Visualizer(networks[CONFIG_B["years"][0]].network, scenario_name="b")
visualizer_b.capacity_dict = capacity_by_tech
visualizer_b.plot_sensitivity_capacity_to_weather_years()
visualizer_cf = Visualizer(networks[CONFIG_B["years"][0]].network, scenario_name="b")
visualizer_cf.plot_capacity_factors(input_data_b)

# TASK C
input_data_c = InputHandler(CONFIG_C)
network_c = NetworkBuilder(CONFIG_C, input_data_c, CONFIG_C["years"][0])
visualizer_c = Visualizer(network_c.network, scenario_name = 'c')
visualizer_c.plot_dispatch_time_series(pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01"))
visualizer_c.plot_dispatch_diff_time_series(
    other=visualizer_a,
    start_summer=pd.Timestamp("2023-07-01"),
    start_winter=pd.Timestamp("2023-12-01"),
)
visualizer_c.plot_annual_electricity_mix()
visualizer_c.plot_storage_behavior(
    start_summer=pd.Timestamp("2023-07-01"),
    start_winter=pd.Timestamp("2023-12-01"),
)
visualizer_c.plot_installed_capacity()

# TASK D
input_data_d = InputHandler(CONFIG_D)
network_d = NetworkBuilder(CONFIG_D, input_data_d, CONFIG_D["years"][0])
visualizer_d = Visualizer(network_d.network, scenario_name = 'd')
visualizer_d.plot_annual_electricity_mix()
visualizer_d.plot_installed_capacity()


# # TASK F
# input_data_f = InputHandler(CONFIG_F)
# REF_CO2 = CONFIG_F["global_CO2_limit"]

# networks_f = {}
# for percent in np.arange(1.0, -0.1, -0.1):
#     co2_limit = percent * REF_CO2
#     CONFIG_F["global_CO2_limit"] = co2_limit
#     try:
#         network_f = NetworkBuilder(CONFIG_F, input_data_f, CONFIG_F["years"][0])
#         networks_f[round(percent, 1)] = network_f
#         print(f"CO2 {percent*100:.0f}% — solved OK")
#     except Exception as e:
#         print(f"CO2 {percent*100:.0f}% — infeasible or error: {e}")

# grouped bar chart: C vs F at 100%
# visualizer_c = Visualizer(network_c.network, scenario_name="c")
# visualizer_f_full = Visualizer(networks_f[max(networks_f.keys())].network, scenario_name="f")
# visualizer_c.plot_scenario_comparison(
#     other=visualizer_f_full,
#     self_label="C (no CO₂ limit)",
#     other_label="F (1990 CO₂ limit)",
#     name="comparison_c_vs_f",
# )
# sensitivity plot
# visualizer_c.plot_co2_sensitivity(
#     networks_f=networks_f,
#     ref_co2=REF_CO2,
#     name="co2_sensitivity",
# )

# # TASK G
# input_data_g = InputHandler(CONFIG_G)
# network_g = NetworkBuilder(CONFIG_G, input_data_g, CONFIG_G["years"][0])

# # TASK H
# input_data_h = InputHandler(CONFIG_H)
# network_h = NetworkBuilder(CONFIG_H, input_data_h, CONFIG_H["years"][0])

# # TASK i
# input_data_i = InputHandler(CONFIG_I)
# network_i = NetworkBuilder(CONFIG_I, input_data_i, CONFIG_I["years"][0])

# # TASK J
# input_data_j = InputHandler(CONFIG_J)
# network_j = NetworkBuilder(CONFIG_J, input_data_j, CONFIG_J["years"][0]))

print('all network optimizations were successful')