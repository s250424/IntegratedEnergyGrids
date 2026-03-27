import numpy
import pypsa
from pathlib import Path
import pandas as pd

technologies_conv = ['coal', 'nuclear', 'biofuels', 'gas'] # conventional energy sources
technologies_vol = ['solar', 'wind_onshore', 'wind_offshore'] # volatile renewable energy sources
CF_BE = pd.read_csv(Path.cwd() / 'entsoe_data' / 'capacity_factors_BE_2023.csv', 
                    index_col=0, 
                    parse_dates=True)
CF_BE.index = pd.to_datetime(CF_BE.index, utc=True).tz_convert(None)
BE_demand = pd.read_csv(Path.cwd() / 'entsoe_data' / 'load_BE_2023.csv',
    index_col=0,
    parse_dates=True
)
BE_demand.index = pd.to_datetime(BE_demand.index, utc=True).tz_convert(None)
BE_demand = BE_demand.resample('h').sum()

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

n.add("Load", name='load_BE', bus = 'bus_BE', p_set = BE_demand['Actual Load'])



