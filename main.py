import pandas as pd

from src.input import InputHandler

CONFIG_DICT = {
    "country": "BE",    # must be the same naming convention as used by ENTSO-E
    "neighbor_countries": ["FR", "NL", "DE_LU"],    # must be the same naming convention as used by ENTSO-E
    "default_year": 2023,   # data in good quality available from ENTSO-E for 2015-2024
    "scenario_years": 2021, # data in good quality available from ENTSO-E for 2015-2024
    "technologies": ["solar", "onwind", "offwind","CCGT","nuclear"]  # must be the same naming convention as in cost list
}

VOLTAGE_LEVEL = 400 # kV, specified by assignment guidelines
REACTANCE = 0.1 # specified by assignment guidelines

inp_hndl = InputHandler(CONFIG_DICT)
print(inp_hndl.load_BE_2023.shape)
