from entsoe import EntsoePandasClient
import pandas as pd 
from pathlib import Path

class InputHandler():
    def __init__(self, config:dict, year:int=2023):
        """
    Initialize the model with configuration and preload all required input data.

    Connects to the ENTSO-E API, then fetches and caches electricity load and
    capacity factor time series for all configured countries and years. Also
    loads technology cost data from a local-copy of a technology CSV file from the Fraunhofer Institute.

    Args:
        config (dict): Configuration dictionary with the following keys:
            - 'countries' (list[str]): ENTSO-E country codes to model (e.g. ['BE', 'FR']).
            - 'years' (list[int]): Calendar years to model (e.g. [2022, 2023]).

    Attributes:
        config (dict): Stored configuration.
        client (EntsoePandasClient): Authenticated ENTSO-E API client.
        load (dict): Maps (country, year) to hourly load DataFrames.
        cf (dict): Maps (country, year) to hourly capacity factor DataFrames.
        tech_data (pd.DataFrame): Technology cost data indexed by (technology, parameter).
        load_heat (dict): Maps (country, year) to hourly heat load DataFrames
    """
        # attach config and client data to class
        self.config = config
        self.client = EntsoePandasClient(api_key='5535fa5d-0280-43f2-9257-0a9295e5105e')

        # get required input data for country and year
        self.load = {}
        self.load_heat = {}
        self.cf = {}
        for country in self.config['countries']:
            self.load[(country, year)] = self._get_load(country, year)
            self.load_heat[(country, year)] = self._get_load_heat(country, year)
            for year in self.config['years']:
                self.cf[(country, year)] = self._get_capacity_factors_volatile_generators(country, year)

        self.tech_data = pd.read_csv('technology_costs/costs_2025.csv', index_col=[0, 1])
    
    def _get_load(self, country:str, year:int) -> pd.DataFrame:
        """
    Retrieve hourly electricity load data for a given country and year.

    Loads are fetched from a local CSV cache if available, otherwise queried
    from the ENTSO-E API and cached for future use. The returned data is
    resampled to hourly resolution.

    Args:
        country (str): ENTSO-E country code (e.g. 'BE', 'FR').
        year (int): The calendar year to retrieve data for.

    Returns:
        pd.DataFrame: Hourly load data with a timezone-naive UTC index.
        """
        path = Path("entsoe_data") / f"load_{country}_{year}.csv"
        if path.exists():
            print("Loading loads from CSV:", path)
            df = pd.read_csv(path, index_col=0)
            df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
            return df.resample('h').sum()
        
        print("Querying loads ENTSOE:", country, year)
        start = pd.Timestamp(f'{year}-01-01', tz="Europe/Brussels")
        end = pd.Timestamp(f'{year+1}-01-01', tz="Europe/Brussels")
        df = self.client.query_load(country, start=start, end=end)
        df.to_csv(path)
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
        return df.resample('h').sum()

    def _get_load_heat(self, country:str, year: int) -> pd.DataFrame:
        """
    Retrieve hourly heating load data for a given country and year from local cache. Loads are read from a local CSV-file obtained from the when2heat-project.

    Args:
        country (str): ENTSO-E country code (e.g. 'BE', 'FR').
        year (int): The calendar year to retrieve data for.

    Returns:
        pd.DataFrame: Hourly heating load data with a timezone-naive UTC index.
        """
        path = Path("entsoe_data") / f"load_heat_{country}_{year}.csv"
        df = pd.read_csv(path, index_col=0, delimiter=";")
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
        return df.resample('h').sum()
        
    def _get_capacity_factors_volatile_generators(self, country:str, year:int) -> pd.DataFrame:
        """
    Retrieve capacity factors for volatile renewable generators for a given country and year.

    Capacity factors are fetched from a local CSV cache if available, otherwise
    computed from ENTSO-E actual generation and installed capacity data, then
    cached for future use. Capacity factor is calculated as actual generation
    divided by installed capacity for solar, onshore wind, and offshore wind.

    Args:
        country (str): ENTSO-E country code (e.g. 'BE', 'FR').
        year (int): The calendar year to retrieve data for.

    Returns:
        pd.DataFrame: Capacity factors with a timezone-naive UTC index and columns
            ['solar', 'onwind', 'offwind'].
        """
        path = Path("entsoe_data") / f"capacity_factors_{country}_{year}.csv"
        if path.exists():
            print("Loading capacity factors from CSV:", path)
            df = pd.read_csv(path, index_col=0)
            df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
            return df
        
        print("Querying capacity factors from ENTSOE:", country, year)
        # Get required data from ENTSOE to calculate cf
        start = pd.Timestamp(f'{year}-01-01', tz="Europe/Brussels")
        end = pd.Timestamp(f'{year+1}-01-01', tz="Europe/Brussels")
        generation = self.client.query_generation(country, start=start, end=end)    # Actual generation per tech (MW)
        capacity = self.client.query_installed_generation_capacity(country, start=start, end=end)   # Installed capacity per tech (MW)
        
        # Calculate cf for desired technologies
        df = pd.DataFrame({
            'solar': self._get_cf(country, generation, capacity, 'Solar'),
            'onwind': self._get_cf(country, generation, capacity, 'Wind Onshore'),
            'offwind': self._get_cf(country, generation, capacity, 'Wind Offshore'),
        })
        df.to_csv(path)
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
        return df
    
    @staticmethod
    def _get_cf(country:str, generation:pd.DataFrame, capacity:pd.DataFrame, key:str) -> pd.Series:
        """
    Calculate the capacity factor for a single generation technology.

    Divides actual generation by installed capacity, resampled and aligned
    to a common hourly index. Returns zeros if the technology is missing
    from either dataset. Results are clipped to [0, 1] and zero-filled
    where installed capacity is zero or data is missing.

    Args:
        country (str): ENTSO-E country code, used only for warning messages.
        generation (pd.DataFrame): Actual generation data with a MultiIndex column
            of (technology, 'Actual Aggregated').
        capacity (pd.DataFrame): Installed capacity data with technology as column names.
        key (str): Technology name to look up (e.g. 'Solar', 'Wind Onshore').

    Returns:
        pd.Series: Hourly capacity factors in [0, 1], indexed to generation.index.
        """
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