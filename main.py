import pandas as pd

from src.input import InputHandler
from scenario import Scenario

CONFIG_A = {
    "countries": ["BE"],    # must be the same naming convention as used by ENTSO-E
    "years": [2023],   # data in good quality available from ENTSO-E for 2015-2024
    "technologies_conv": ["CCGT","nuclear"],  # must be the same naming convention as in cost list
    "technologies_vol": ["solar", "onwind", "offwind"],
    'voltage_level': [400], # kV, specified by assignment guidelines
    'reactance': [0.1] # specified by assignment guidelines`
}

CONFIG_B = {
    "countries": ["BE"],    # must be the same naming convention as used by ENTSO-E
    "years": [2020, 2021, 2022, 2024], # data in good quality available from ENTSO-E for 2015-2024
    "technologies_conv": ["CCGT","nuclear"],  # must be the same naming convention as in cost list
    "technologies_vol": ["solar", "onwind", "offwind"],
    "voltage_level": [400], # kV, specified by assignment guidelines
    'reactance': [0.1] # specified by assignment guidelines`
}

CONFIG_C = {
    "countries": ["BE"],    # must be the same naming convention as used by ENTSO-E
    "years": [2020, 2021, 2022, 2024], # data in good quality available from ENTSO-E for 2015-2024
    "technologies_conv": ["CCGT","nuclear"],  # must be the same naming convention as in cost list
    "technologies_vol": ["solar", "onwind", "offwind"],
    'voltage_level': [400], # kV, specified by assignment guidelines
    'reactance': [0.1] # specified by assignment guidelines`
}

CONFIG_D = {
    "countries": ["BE", "FR", "NL", "DE_LU"],    # must be the same naming convention as used by ENTSO-E
    "years": [2020, 2021, 2022, 2024], # data in good quality available from ENTSO-E for 2015-2024
    "technologies_conv": ["CCGT","nuclear"],  # must be the same naming convention as in cost list
    "technologies_vol": ["solar", "onwind", "offwind"],
    'voltage_level': [400], # kV, specified by assignment guidelines
    'reactance': [0.1] # specified by assignment guidelines`
}


###Task a
input_data_a = InputHandler(CONFIG_A)
scenario_a = Scenario(CONFIG_A, input_data_a)
network_BE = scenario_a.run_single_year()

###Task b
input_data_b = InputHandler(CONFIG_B)
scenario_b = Scenario(CONFIG_B, input_data_b)
network_BE_SA = Scenario.run_multiple_years(input_data_b)

###Task c
input_data_c = InputHandler(CONFIG_C)
scenario_c = Scenario(CONFIG_C, input_data_c)
network_BE_storage = Scenario.run_with_storage(input_data_c)

###Task d
input_data_d = InputHandler(CONFIG_D)
scenario_d = Scenario(CONFIG_D, input_data_d)
network_BE_connections = Scenario.run_multi_countries(input_data_d)

print('all network optimizations were successful')