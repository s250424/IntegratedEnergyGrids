import numpy
import pypsa
from pathlib import Path
import pandas as pd

technologies_conv = ['coal', 'nuclear', 'biofuels', 'gas']
technologies_vol = ['solar', 'wind_onshore', 'wind_offshore']
CF_BE = pd.read_csv(Path.cwd() / 'entsoe_data' / 'capacity_factors_BE_2023.csv', index_col=0, parse_dates=True)
BE_demand = pd.read_csv(Path.cwd() / 'entsoe_data' / 'load_BE_2023.csv', index_col=0, parse_dates=True)

n = pypsa.Network()
n.set_snapshots(BE_demand.index)

n.add("Bus", "bus_BE")

for i in technologies_conv:
    n.add("Generator", 
          i, 
          bus = 'bus_BE', 
          p_nom_extendable = True,
          p_nom_min = 0
          )

for i in technologies_vol:
    n.add("Generator", 
          i, 
          bus = 'bus_BE', 
          p_nom_extendable = True,
          p_nom_min = 0, 
          p_max_pu = CF_BE[f'{i}_cf'],
          marginal_cost = 0
          )

n.add("Load", bus = 'bus_BE', p_set = BE_demand['Actual Load'])



