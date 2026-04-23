import copy

import pandas as pd

from src.input import InputHandler
from src.networkbuilder import NetworkBuilder
from src.visualizer import Visualizer

""">>>> SPECIFY CONFIGURATION-DICTIONARIES FOR EACH TASK <<<<"""
CONFIG_A = {
    "countries": ["BE"],    # must be the same naming convention as used by ENTSO-E
    "years": [2023],   # data in good quality available from ENTSO-E for 2015-2024
    "technologies_conv": {"BE": ["CCGT", "nuclear", 'biomass CHP']},  # must be the same naming convention as in cost list
    "technologies_vol": {"BE": ["solar-rooftop", "onwind", "offwind"]},
    'voltage_level': 400, # kV, specified by assignment guidelines
    'reactance': 0.1 # specified by assignment guidelines`
}

CONFIG_B = copy.deepcopy(CONFIG_A)
CONFIG_B["years"] = 2020, 2021, 2022, 2024, # data in good quality available from ENTSO-E for 2015-2024

CONFIG_C = copy.deepcopy(CONFIG_A)
CONFIG_C["technologies_storage"] = ["Pumped-Storage-Hydro-bicharger"]

CONFIG_D = copy.deepcopy(CONFIG_A)
CONFIG_D["countries"] = ["BE", "FR", "NL", "DE_LU"]    # must be the same naming convention as used by ENTSO-E
CONFIG_D["technologies_conv"]["FR"] = ["CCGT", "nuclear", 'biomass CHP']    # TODO adjust based on real technology mix
CONFIG_D["technologies_vol"]["FR"] = ["solar-rooftop", "onwind", "offwind"] # TODO adjust based on real technology mix
CONFIG_D["technologies_conv"]["NL"] = ["CCGT", "nuclear", 'biomass CHP']    # TODO adjust based on real technology mix
CONFIG_D["technologies_vol"]["NL"] = ["solar-rooftop", "onwind", "offwind"] # TODO adjust based on real technology mix
CONFIG_D["technologies_conv"]["DE_LU"] = ["CCGT", "nuclear", 'biomass CHP'] # TODO adjust based on real technology mix
CONFIG_D["technologies_vol"]["DE_LU"] = ["solar-rooftop", "onwind", "offwind"]  # TODO adjust based on real technology mix

CONFIG_D ["transmission_lines"] = [
    {"name": "BE-FR",    "bus0": "BE",    "bus1": "FR",    "x": 0.1, "s_nom": 3500},
    {"name": "BE-NL",    "bus0": "BE",    "bus1": "NL",    "x": 0.1, "s_nom": 3000},
    {"name": "BE-DE_LU", "bus0": "BE",    "bus1": "DE_LU", "x": 0.1, "s_nom": 2500},
    {"name": "FR-DE_LU", "bus0": "FR",    "bus1": "DE_LU", "x": 0.1, "s_nom": 3000},
    {"name": "NL-DE_LU", "bus0": "NL",    "bus1": "DE_LU", "x": 0.1, "s_nom": 3500},
]

CONFIG_F = copy.deepcopy(CONFIG_C)
CONFIG_F["global_CO2_limit"] = 20000   # TODO find CO2 emissions / CO2 allowance

CONFIG_G = copy.deepcopy(CONFIG_D)
CONFIG_G["CH4_lines"] = {}  # TODO add lines for CH4

CONFIG_H = copy.deepcopy(CONFIG_G)
CONFIG_H["global_CO2_limit"] = 20000   # TODO find CO2 emissions / CO2 allowance

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

# # TASK B
# input_data_b = InputHandler(CONFIG_B)
# networks = {}
# for year in CONFIG_B["years"]:
#     network_b = NetworkBuilder(CONFIG_B, input_data_b, year)
#     networks[year] = network_b

# # TASK C
# input_data_c = InputHandler(CONFIG_C)
# network_c = NetworkBuilder(CONFIG_C, input_data_c, CONFIG_C["years"][0])

# # TASK D
# input_data_d = InputHandler(CONFIG_D)
# network_d = NetworkBuilder(CONFIG_D, input_data_d, CONFIG_D["years"][0])

# # TASK F
# input_data_f = InputHandler(CONFIG_F)
# network_f = NetworkBuilder(CONFIG_F, input_data_f, CONFIG_F["years"][0])

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