import numpy
import pypsa
from pathlib import Path
import pandas as pd

class NetworkBuilder:
    """
    Initialize the builder with a selected weather year
    """
    def __init__(self, weather_year: int= 2023):
        self.weather_year = weather_year
        
        # Define available technologies
        self.technologies_conv = ['coal', 'nuclear', 'biofuels', 'gas']
        self.technologies_vol = ['solar', 'wind_onshore', 'wind_offshore']

        # Placeholders for data and network
        self.cf_be = None
        self.be_demand = None
        self.network = None
    
    def load_data(self):
        # Load renewable capacity factors
        self.cf_be = pd.read_csv(
            Path.cwd() / 'entsoe_data' / f'capacity_factors_BE_{self.weather_year}.csv',
            index_col=0,
            parse_dates=True
        )
        self.cf_be.index = pd.to_datetime(self.cf_be.index, utc=True).tz_convert(None)

        # Load demand data
        self.be_demand = pd.read_csv(
            Path.cwd() / 'entsoe_data' / f'load_BE_{self.weather_year}.csv',
            index_col=0,
            parse_dates=True
        )
        self.be_demand.index = pd.to_datetime(self.be_demand.index, utc=True).tz_convert(None)

        # Convert to hourly resolution
        self.be_demand = self.be_demand.resample('h').sum()

    def create_network(self):
        """
        Create an empty PyPSA network and define time snapshots.
        """
        self.network = pypsa.Network()
        self.network.set_snapshots(self.be_demand.index)
        self.network.add("Bus", "bus_BE")

    def add_conventional_generators(self):
        for tech in self.technologies_conv:
            self.network.add(
                "Generator",
                tech,
                bus="bus_BE",
                p_nom_extendable=True,
                p_nom_min=0
            )
    
    def add_renewable_generators(self):
        for tech in self.technologies_vol:
            self.network.add(
                "Generator",
                tech,
                bus="bus_BE",
                p_nom_extendable=True,
                p_nom_min=0,
                p_max_pu=self.cf_be[f"{tech}_cf"],
                marginal_cost=0
            )
    
    def add_load(self):
        self.network.add(
            "Load",
            "load_BE",
            bus="bus_BE",
            p_set=self.be_demand["Actual Load"]
        )

    def build(self):
        self.load_data()
        self.create_network()
        self.add_conventional_generators()
        self.add_renewable_generators()
        self.add_load()
        return self.network
    
if __name__ == "__main__":
    builder = NetworkBuilder(weather_year=2023)
    n = builder.build()

    print(n)
    print("\nBuses:")
    print(n.buses)

    print("\nGenerators:")
    print(n.generators)

    print("\nLoads:")
    print(n.loads)

    print("\nNumber of snapshots:")
    print(len(n.snapshots))