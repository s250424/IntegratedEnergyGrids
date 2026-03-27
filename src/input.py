from entsoe import EntsoePandasClient
import pandas as pd 
from pathlib import Path

class InputHandler():
    def __init__(self, config_dict:dict):
        # Create cache directory if it doesn't exist
        self.cache_dir = Path("entsoe_data")
        self.cache_dir.mkdir(exist_ok=True)

        self.client = EntsoePandasClient(api_key='5535fa5d-0280-43f2-9257-0a9295e5105e')
        start = pd.Timestamp(f'{config_dict["default_year"]}-01-01', tz="Europe/Brussels")
        end = pd.Timestamp(f'{config_dict["default_year"] + 1}-01-01', tz="Europe/Brussels")

        # for default year, get load and cf of main country
        setattr(self, f'load_{config_dict["country"]}_{config_dict["default_year"]}', self._get_or_cache_hourly_load(config_dict["country"], config_dict["default_year"], start, end))
        setattr(self, f'cf_{config_dict["country"]}_{config_dict["default_year"]}', self._get_or_cache_capacity_factors_renewables(config_dict["country"], config_dict["default_year"], start, end))

        # for default year, get load and cf of neighbor countries
        for neighbor in config_dict["neighbor_countries"]:
            setattr(self, f'load_{neighbor}_{config_dict["default_year"]}', self._get_or_cache_hourly_load(neighbor, config_dict["default_year"], start, end))
            setattr(self, f'cf_{neighbor}_{config_dict["default_year"]}', self._get_or_cache_capacity_factors_renewables(neighbor, config_dict["default_year"], start, end))

        # for scenario years, get load and cf of main country
        if isinstance(config_dict["scenario_years"], list):
            for scenario_year in config_dict["scenario_years"]:
                start_scenario = pd.Timestamp(f'{scenario_year}-01-01', tz="Europe/Brussels")
                end_scenario = pd.Timestamp(f'{scenario_year + 1}-01-01', tz="Europe/Brussels")
                setattr(self, f'load_{config_dict["country"]}_{scenario_year}', self._get_or_cache_hourly_load(config_dict["country"], scenario_year, start_scenario, end_scenario))
                setattr(self, f'cf_{config_dict["country"]}_{scenario_year}', self._get_or_cache_capacity_factors_renewables(config_dict["country"], scenario_year, start_scenario, end_scenario))
        elif isinstance(config_dict["scenario_years"], int):
                start_scenario = pd.Timestamp(f'{config_dict["scenario_years"]}-01-01', tz="Europe/Brussels")
                end_scenario = pd.Timestamp(f'{config_dict["scenario_years"] + 1}-01-01', tz="Europe/Brussels")
                setattr(self, f'load_{config_dict["country"]}_{config_dict["scenario_years"]}', self._get_or_cache_hourly_load(config_dict["country"], config_dict["scenario_years"], start_scenario, end_scenario))
                setattr(self, f'cf_{config_dict["country"]}_{config_dict["scenario_years"]}', self._get_or_cache_capacity_factors_renewables(config_dict["country"], config_dict["scenario_years"], start_scenario, end_scenario))

        self.technology_costs_all = pd.read_csv('technology-data/output/costs_2025.csv', index_col=[0, 1])
        self.technology_costs = {}
        for technology in config_dict["technologies"]:
            self.technology_costs[technology] = self._get_technology_costs(technology)


    def _get_technology_costs(self, technology: str):
        return {
            "inv": self._get_cost(self.technology_costs_all, technology, "investment"),
            "fom": self._get_cost(self.technology_costs_all, technology, "FOM"),
            "vom": self._get_cost(self.technology_costs_all, technology, "VOM"),
        }

    def _get_hourly_load(self, country:str, start: pd.Timestamp, end:pd.Timestamp) -> pd.DataFrame: 
        return self.client.query_load(country, start=start, end=end)
    
    def _get_or_cache_hourly_load(self, country:str, year:int, start: pd.Timestamp, end:pd.Timestamp ) -> pd.DataFrame:
        path = self.cache_dir / f"load_{country}_{year}.csv"
        if path.exists():
            print("Loading loads from CSV:", path)
            return pd.read_csv(path, index_col=0,  parse_dates=True)
        
        print("Querying loads ENTSOE:", country, year)
        df = self._get_hourly_load(country, start, end)
        df.to_csv(path)
        return df


    def _get_capacity_factors_renewables(self, country:str, start: pd.Timestamp, end:pd.Timestamp) -> pd.DataFrame:
        # Actual generation per technology (MW)
        generation = self.client.query_generation(country, start=start, end=end)

        # Installed capacity per technology (MW) - returned per month, need to resample
        capacity = self.client.query_installed_generation_capacity(country, start=start, end=end)

        return pd.DataFrame({
            'solar_cf':         self._get_cf(country, generation, capacity, 'Solar'),
            'wind_onshore_cf':  self._get_cf(country, generation, capacity, 'Wind Onshore'),
            'wind_offshore_cf': self._get_cf(country, generation, capacity, 'Wind Offshore'),
        })

    def _get_or_cache_capacity_factors_renewables(self, country:str, year:int, start: pd.Timestamp, end:pd.Timestamp ) -> pd.DataFrame:
        path = self.cache_dir / f"capacity_factors_{country}_{year}.csv"
        if path.exists():
            print("Loading capacity factors from CSV:", path)
            return pd.read_csv(path, index_col=0,  parse_dates=True)
        
        print("Querying capacity factors from ENTSOE:", country, year)
        df = self._get_capacity_factors_renewables(country, start, end)
        df.to_csv(path)
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