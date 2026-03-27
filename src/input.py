from entsoe import EntsoePandasClient
import pandas as pd 
from pathlib import Path

class InputHandler():
    def __init__(self, config):
        # Create cache directory if it doesn't exist
        self.cache_dir = Path("entsoe_data")
        self.cache_dir.mkdir(exist_ok=True)
        self.config = config
        self.client = EntsoePandasClient(api_key='5535fa5d-0280-43f2-9257-0a9295e5105e')

        # depending on config data get data for countries and years
        self.load = {}
        self.cf = {}
        for country in self.config['countries']:
            for year in self.config['years']:
                start = pd.Timestamp(f'{year}-01-01', tz="Europe/Brussels")
                end = pd.Timestamp(f'{year+1}-01-01', tz="Europe/Brussels")
                self.load[(country, year)] = self._get_or_cache_load(country, year, start, end)
                self.cf[(country, year)] = self._get_or_cache_capacity_factors_renewables(country, year, start, end)


        self.technology_costs_all = pd.read_csv('technology-data/outputs/costs_2025.csv', index_col=[0, 1])
        self.technology_costs = {}
        all_technologies = self.config["technologies_conv"] + self.config["technologies_vol"]
        for tech in all_technologies:
            self.technology_costs[tech] = self._get_technology_costs(tech)


    def _get_technology_costs(self, technology: str):
        return {
            "inv": self._get_cost(self.technology_costs_all, technology, "investment"),
            "fom": self._get_cost(self.technology_costs_all, technology, "FOM"),
            "vom": self._get_cost(self.technology_costs_all, technology, "VOM"),
        }

    def _get_load(self, country:str, start: pd.Timestamp, end:pd.Timestamp) -> pd.DataFrame: 
        return self.client.query_load(country, start=start, end=end)
    
    def _get_or_cache_load(self, country, year, start, end):
        path = self.cache_dir / f"load_{country}_{year}.csv"
        if path.exists():
            print("Loading loads from CSV:", path)
            df = pd.read_csv(path, index_col=0)
            df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
            return df.resample('h').sum()
        
        print("Querying loads ENTSOE:", country, year)
        df = self._get_load(country, start, end)
        df.to_csv(path)
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
        return df.resample('h').sum()
    
    def _get_capacity_factors_renewables(self, country:str, start: pd.Timestamp, end:pd.Timestamp) -> pd.DataFrame:
        # Actual generation per technology (MW)
        generation = self.client.query_generation(country, start=start, end=end)

        # Installed capacity per technology (MW) - returned per month, need to resample
        capacity = self.client.query_installed_generation_capacity(country, start=start, end=end)

        return pd.DataFrame({
            'solar-rooftop':         self._get_cf(country, generation, capacity, 'Solar'),
            'onwind':  self._get_cf(country, generation, capacity, 'Wind Onshore'),
            'offwind': self._get_cf(country, generation, capacity, 'Wind Offshore'),
        })

    def _get_or_cache_capacity_factors_renewables(self, country:str, year:int, start: pd.Timestamp, end:pd.Timestamp ) -> pd.DataFrame:
        path = self.cache_dir / f"capacity_factors_{country}_{year}.csv"
        if path.exists():
            print("Loading capacity factors from CSV:", path)
            df = pd.read_csv(path, index_col=0)
            df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
            return df
        
        print("Querying capacity factors from ENTSOE:", country, year)
        df = self._get_capacity_factors_renewables(country, start, end)
        df.to_csv(path)
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
        return df
    
    @staticmethod
    def _get_cost(df, technology, param):
        try:
            return df.loc[(technology, param), "value"]
        except KeyError:
            return 0.0
    
    @staticmethod
    def _get_cf(country, generation, capacity, key):
        try:
            cap = capacity[key].resample('h').ffill().reindex(generation.index, method='ffill')
        except KeyError:
            print(f"Warning: '{key}' not found in CAPACITY for {country}, returning zeros.")
            return pd.Series(0.0, index=generation.index)
        
        try:
            gen = generation[(key, 'Actual Aggregated')]
        except KeyError:
            print(f"Warning: '{key}' not found in GENERATION for {country}, returning zeros.")
            return pd.Series(0.0, index=generation.index)

        cf = (gen / cap).clip(0, 1)
        cf = cf.where(cap > 0, other=0.0)
        return cf.fillna(0.0)