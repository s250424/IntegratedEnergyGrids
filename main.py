import copy

import pandas as pd

from src.input import InputHandler
from src.scenario import Scenario
from src.visualizer import Visualizer


""">>>> SPECIFY CONFIGURATION-DICTIONARIES FOR EACH TASK <<<<"""
CONFIG_A = {
    "countries": ["BE"],    # must be the same naming convention as used by ENTSO-E
    "years": [2023],   # data in good quality available from ENTSO-E for 2015-2024
    "technologies_conv": ["CCGT","nuclear", 'biomass CHP'],  # must be the same naming convention as in cost list
    "technologies_vol": ["solar-rooftop", "onwind", "offwind"],
    "technologies_storage": [],
    'voltage_level': [400], # kV, specified by assignment guidelines
    'reactance': [0.1] # specified by assignment guidelines`
}

CONFIG_B = copy.deepcopy(CONFIG_A)
CONFIG_B["years"] = 2020, 2021, 2022, 2024, # data in good quality available from ENTSO-E for 2015-2024

CONFIG_C = copy.deepcopy(CONFIG_A)
CONFIG_C["technologies_storage"] = ["Pumped-Storage-Hydro-bicharger"]

CONFIG_D = copy.deepcopy(CONFIG_A)
CONFIG_D["countries"] = ["BE", "FR", "NL", "DE_LU"]    # must be the same naming convention as used by ENTSO-E

CONFIG_F = copy.deepcopy(CONFIG_C)
CONFIG_F["CO2_limit"] = 20000   # TODO find CO2 emissions / CO2 allowance

CONFIG_G = copy.deepcopy(CONFIG_D)

""">>>> SOLVE THE OPTIMIZATION PROBLEMS<<<<"""
# TASK A
# input_data_a = InputHandler(CONFIG_A)
# scenario_a = Scenario(CONFIG_A, input_data_a)
# network_BE = scenario_a.run_single_year(year=CONFIG_A['years'][0])
# visualizer_a = Visualizer(network_BE, scenario_name = 'a')
# visualizer_a.plot_dispatch_time_series(pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01"))
# visualizer_a.plot_annual_electricity_mix()

# TASK B
# input_data_b = InputHandler(CONFIG_B)
# scenario_b = Scenario(CONFIG_B, input_data_b)
# network_BE_SA = scenario_b.run_multiple_years()
# visualizer_a = Visualizer(network_BE, scenario_name = 'b')
# visualizer_a.plot_dispatch_time_series(pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01"))
# visualizer_a.plot_annual_electricity_mix()

# TASK C
input_data_c = InputHandler(CONFIG_C)
scenario_c = Scenario(CONFIG_C, input_data_c)
network_BE_storage = scenario_c.run_with_storage()
visualizer_c = Visualizer(network_BE_storage, scenario_name='c')
visualizer_c.plot_dispatch_time_series(pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01"))
visualizer_c.plot_annual_electricity_mix(name="c_annual_electricity_mix")


# TASK D
# input_data_d = InputHandler(CONFIG_D)
# scenario_d = Scenario(CONFIG_D, input_data_d)
# network_BE_connections = scenario_d.run_multi_countries()
# visualizer_a = Visualizer(network_BE, scenario_name = 'd')
# visualizer_a.plot_dispatch_time_series(pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01"))
# visualizer_a.plot_annual_electricity_mix()

# TASK F
input_data_f = InputHandler(CONFIG_F)
scenario_f = Scenario(CONFIG_F, input_data_f) # TODO add 
network_BE_CO2limit = scenario_f.run_with_global_co2_limit()
visualizer_f = Visualizer(network_BE_CO2limit, scenario_name='e')
visualizer_f.plot_dispatch_time_series(pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01"))
visualizer_f.plot_annual_electricity_mix(name="e_annual_electricity_mix")


print('all network optimizations were successful')