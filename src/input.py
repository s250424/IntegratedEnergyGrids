from entsoe import EntsoePandasClient
import pandas as pd 

class InputHandler():
    def __init__(self):
        self.client = EntsoePandasClient(api_key='5535fa5d-0280-43f2-9257-0a9295e5105e')

        start = pd.Timestamp('20220101', tz='Europe/Brussels')
        end   = pd.Timestamp('20230101', tz='Europe/Brussels')

        # Hourly load (demand)
        self.load_belgium = self._get_hourly_load('BE')
        self.cf_belgium_2022 = self._get_capacity_factors_renewables('BE')
        self.cf_belgium_2021 = self._get_capacity_factors_renewables('BE')

    def _get_hourly_load(self, country:str, start: pd.Timestamp = pd.Timestamp('20220101', tz='Europe/Brussels'), end:pd.Timestamp = pd.Timestamp('20230101', tz='Europe/Brussels')) -> pd.DataFrame: 
        return self.client.query_load(country, start=start, end=end)


    def _get_capacity_factors_renewables(self, country:str, start: pd.Timestamp = pd.Timestamp('20220101', tz='Europe/Brussels'), end:pd.Timestamp = pd.Timestamp('20230101', tz='Europe/Brussels')) -> pd.DataFrame:
        # Capacity factors one year for solar and wind
        # Actual generation per technology (MW)
        generation = self.client.query_generation(country, start=start, end=end)

        # Installed capacity per technology (MW) - returned per month, need to resample
        capacity = self.client.query_installed_generation_capacity(country, start=start, end=end)

        # Solar - Reindex capacity to hourly and forward-fill
        solar_cap = capacity['Solar'].resample('h').ffill().reindex(generation.index, method='ffill')
        solar_gen = generation[('Solar', 'Actual Aggregated')]  # MW
        solar_cf = solar_gen / solar_cap  # dimensionless, 0–1

        # Wind Onshore
        wind_cap = capacity['Wind Onshore'].resample('h').ffill().reindex(generation.index, method='ffill')
        wind_gen = generation[('Wind Onshore', 'Actual Aggregated')]
        wind_cf = wind_gen / wind_cap

        # Wind Offshore
        wind_off_cap = capacity['Wind Offshore'].resample('h').ffill().reindex(generation.index, method='ffill')
        wind_off_gen = generation[('Wind Offshore', 'Actual Aggregated')]
        wind_off_cf = wind_off_gen / wind_off_cap

        # clip to 0,1 and return as a combined dataframe
        solar_cf    = solar_cf.clip(0, 1)
        wind_cf     = wind_cf.clip(0, 1)
        wind_off_cf = wind_off_cf.clip(0, 1)

        df_cf = pd.DataFrame({
            'solar_cf':         solar_cf,
            'wind_onshore_cf':  wind_cf,
            'wind_offshore_cf': wind_off_cf,
        })
        return df_cf





"""1. Demand / Load Data

Hourly electricity demand for your chosen region (8760 hours/year)
Sources: ENTSO-E Transparency Platform (entso-e.eu), Open Power System Data (open-power-system-data.org)

2. Renewable Resource Data (per weather year)

Solar irradiance → capacity factors for solar PV (hourly)
Wind speed → capacity factors for onshore/offshore wind (hourly)
Sources: renewables.ninja (easiest), ERA5 reanalysis via Copernicus, or the atlite library (used directly with PyPSA)
For part b) you need multiple weather years (e.g. 2013–2022)

3. Generator Technology Data (costs + parameters)
For each technology (solar PV, onshore wind, offshore wind, CCGT, nuclear, etc.) you need:

Capital cost (€/kW or €/MW)
Marginal/variable cost (€/MWh)
Fixed O&M cost (€/kW/year)
Lifetime (years, for annualisation)
Efficiency (for thermal plants)
CO₂ emissions (tCO₂/MWh_fuel), if you add a carbon price
Source: PyPSA technology-data repo on GitHub (github.com/PyPSA/technology-data) — this is the standard reference, based on DEA and NREL data

4. Fuel & Carbon Prices

Natural gas, coal, nuclear fuel prices (€/MWh_thermal)
CO₂ price (€/tCO₂) — e.g. current EU ETS price
Source: IEA, Eurostat, or just state your assumptions

5. Storage Technology Data (part c)

Battery (Li-ion): capital cost (€/kW power, €/kWh energy), round-trip efficiency, self-discharge
Pumped hydro: similar parameters
Hydrogen/electrolysis: if you want long-duration storage
Source: PyPSA technology-data, NREL ATB

6. Network / Interconnector Data (part d)

Neighbouring countries: at least 3 neighbours + one closed cycle (loop)
Existing line capacities (MW) between countries
Source: ENTSO-E Transparency Platform → Cross-border flows / NTC values; also the PyPSA-Eur dataset
Line parameters: voltage 400 kV, reactance x = 0.1 (given in the problem), line length (km) between nodes
Bus locations (lat/lon of each country's representative node)

7. Discount Rate

A weighted average cost of capital (WACC), typically 7–8% for Europe
Used to annualise capital costs: annuity factor = r / (1 - (1+r)^(-lifetime))
"""