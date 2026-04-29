import pypsa

from src.input import InputHandler

class NetworkBuilder:
    """Builds and runs the Pypsa-optimization-model."""
    def __init__(self, config:dict, input_data:InputHandler, year:int):
        """
    Initialize the network model, build it, and run the optimization.

    Stores references to configuration and input data, then immediately
    constructs and optimizes the PyPSA network for the given year.

    Args:
        config (dict): Model configuration specifying countries, technologies,
            voltage level, CO2 limits, and other network parameters.
        input_data: Object containing all preprocessed input data with attributes:
            - load: electricity demand time series per country and year.
            - load_heat: heat demand time series per country and year.
            - tech_data: technology cost and performance parameters.
            - cf: capacity factor time series per country and year.
        year (int): The simulation year for which the network is built
            and optimized.
        """
        # Rename inputs for more convenient use
        self.config = config
        self.load = input_data.load
        self.load_heat = input_data.load_heat
        self.tech_data = input_data.tech_data
        self.cf = input_data.cf
        
        # Build and optimize the network
        self._build_network(year)
        self.network.optimize()

    def _build_network(self, year:int):
        """
    Initialize and assemble the full PyPSA network for a given simulation year.

    Creates a fresh PyPSA network and sequentially adds all configured components:

    - Buses, carriers, and energy stocks (always).
    - Loads (always).
    - Dispatchable and volatile generators (always).
    - Transmission lines: only if more than one country is configured.
    - Storage units: only if storage technologies are specified in config.
    - Global CO2 constraint: only if a CO2 limit is specified in config.

    Args:
        year (int): The simulation year, passed to volatile generator and
            load methods to select the appropriate time series data.
        """
        # INITIALIZE PYPSA NETWORK
        self.network = pypsa.Network()
        
        # ADD COMPONENTS TO PYPSA NETWORK
        self._add_buses_carrier_stocks()
        load_year = self.config.get("load_year", year)
        self._add_loads(load_year)
        self._add_dispatchable_generators()
        self._add_volatile_generators(year)
        if len(self.config["countries"]) > 1:
            self._add_transmission_lines()
        if self.config.get("technologies_storage"):
            self._add_storage()
        if self.config.get("global_CO2_limit"):
            self._add_global_co2_limit()

    def _add_buses_carrier_stocks(self):
        """
    Add buses, energy stocks, and carriers to the network for each country.

    For each configured country, adds four buses (electricity, CH4, heat, biomass)
    and corresponding storage stocks:

    - Biomass stock: always unlimited (e_initial=1e20).
    - CH4 stock: if CH4 transmission lines are enabled, only the Netherlands ('NL')
      gets an unlimited initial stock (acting as the gas import hub); all other
      countries start empty. Without CH4 lines, all countries get unlimited stock.

    Registers the following carriers with CO2 intensities (t CO2/MWh):

    - ch4, biomass, coal: intensities sourced from technology data.
    - electricity, heat: no CO2 intensity.
    - nuclear, solar, offwind, onwind: fixed lifecycle emission factors.
        """
        for country in self.config["countries"]:
            # add busses
            self.network.add("Bus", name=f"bus_{country}", v_nom=self.config["voltage_level"], carrier="electricity")
            self.network.add("Bus", name=f"bus_{country}_ch4", carrier="ch4")
            self.network.add("Bus", name=f"bus_{country}_heat", carrier="heat")
            self.network.add("Bus", name=f"bus_{country}_biomass", carrier="biomass")

            # add stocks
            self.network.add("Store", f"biomass_stock_{country}", e_initial=1e20, e_nom=1e20, bus=f"bus_{country}_biomass")
            if self.config.get("CH4_lines"):
                if country == "NL":
                    self.network.add("Store", f"ch4_stock_{country}", e_initial=1e20, e_nom=1e20, bus=f"bus_{country}_ch4")
                else:
                    self.network.add("Store", f"ch4_stock_{country}", e_initial=0, e_nom=1e20, bus=f"bus_{country}_ch4")
            else:
                self.network.add("Store", f"ch4_stock_{country}", e_initial=1e20, e_nom=1e20, bus=f"bus_{country}_ch4")

        # dispatchable with stock & busses
        self.network.add("Carrier", "ch4", co2_emissions=self.tech_data.loc[("gas", "CO2 intensity"), "value"]) # t CO2/MWh
        self.network.add("Carrier", "biomass", co2_emissions=self.tech_data.loc[("solid biomass", "CO2 intensity"), "value"])   # t CO2/MWh
        self.network.add("Carrier", "electricity")
        self.network.add("Carrier", "heat")

        # dispatchable without stock & busses
        self.network.add("Carrier", "coal", co2_emissions=self.tech_data.loc[("coal", "CO2 intensity"), "value"])   # t CO2/MWh
        self.network.add("Carrier", "nuclear", co2_emissions=0.012) # t CO2/MWh, from Claude

        # volatile
        self.network.add("Carrier", "solar", co2_emissions=0.043)   # t CO2/MWh, from Claude
        self.network.add("Carrier", "offwind", co2_emissions=0.012) # t CO2/MWh, from Claude
        self.network.add("Carrier", "onwind", co2_emissions=0.011)  #   , from Claude

        # storage
        self.network.add("Carrier", "Pumped-Storage-Hydro-bicharger")
        self.network.add("Carrier", "Lithium-Ion-LFP-bicharger")



    def _add_loads(self, year:int=2023):
        """
    Add electricity and optional heat loads to the network for a given year.

    Iterates over all configured countries, setting network snapshots to match
    the electricity demand index and adding an electricity 'Load' per country.
    If heat is enabled in the config, a corresponding heat 'Load' is also added
    to the country's heat bus.

    Args:
        year (int): The simulation year used to select demand time series.
            Defaults to 2023.

    Notes:
        - Network snapshots are overwritten by each country's demand index;
          all countries should share the same time index.
        - Electricity load is sourced from self.load[(country, year)].
        - Heat load is sourced from self.load_heat[(country, year)], only
          added when 'include_heat' is set in config.
        """
        for country in self.config["countries"]:
            demand = self.load[(country, year)]
            self.network.set_snapshots(demand.index)
            self.network.add(
                "Load",
                name=f"load_{country}",
                bus=f"bus_{country}",
                p_set=demand["Actual Load"],
            )
            if self.config.get("include_heat"):
                heating_demand = self.load_heat[(country, 2023)]
                self.network.add(
                    "Load",
                    name=f"load_{country}_heat",
                    bus=f"bus_{country}_heat",
                    p_set=heating_demand["Actual Load"],
                )

    def _add_dispatchable_generators(self):
        """
    Add dispatchable generators to the network for each country and technology.

    Iterates over all configured countries and dispatchable technologies, adding
    capacity-extendable components with costs and efficiencies sourced from
    technology data. Capital cost includes fixed O&M (FOM) as a fraction of
    investment. Marginal cost uses VOM if available, otherwise zero.

    Technology-specific component types and bus configurations:

    - biomass CHP: 'Link' drawing from biomass bus, outputting to electricity
      and heat buses with separate electrical and heat efficiencies.
    - CCGT: 'Link' drawing from CH4 bus, outputting to electricity and heat buses.
    - gas boiler steam: 'Link' drawing from CH4 bus, outputting to heat bus only.
    - industrial heat pump (high temperature): 'Link' drawing from electricity bus,
      outputting to heat bus.
    - OCGT: 'Link' drawing from CH4 bus, outputting to electricity bus only.
    - all others: standard 'Generator' connected to the country electricity bus.
        """
        for country in self.config["countries"]:
            for tech in self.config["technologies_disp"]:

                # Specify variables to be used for generator addition to network
                name = f"generator_disp_{country}_{tech}"
                marginal_cost = self.tech_data.loc[(tech, "VOM"), "value"] if (tech, "VOM") in self.tech_data.index else 0
                lifetime = self.tech_data.loc[(tech, "lifetime"), "value"]
                capital_cost = self.tech_data.loc[(tech, "investment"), "value"]+ self.tech_data.loc[(tech, "investment"), "value"]*(self.tech_data.loc[(tech, "FOM"), "value"]/100)
                efficiency = self.tech_data.loc[(tech, "efficiency"), "value"]

                # Add generators to network
                if tech == "biomass CHP":
                    self.network.add(
                        "Link", name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus0=f"bus_{country}_biomass", 
                        bus1=f"bus_{country}",
                        bus2=f"bus_{country}_heat",
                        carrier = 'biomass',
                        efficiency2=self.tech_data.loc[(tech, "efficiency-heat"), "value"])
                elif tech == "CCGT":
                    self.network.add(
                        "Link", name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus0=f"bus_{country}_ch4", 
                        bus1=f"bus_{country}",
                        bus2=f"bus_{country}_heat",
                        carrier = 'ch4',
                        efficiency2=self.tech_data.loc[(tech, "efficiency"), "value"])     # TODO add heat efficiency                
                elif tech == "gas boiler steam":
                    self.network.add(
                        "Link", name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus0=f"bus_{country}_ch4", 
                        bus1=f"bus_{country}_heat",
                        carrier = 'ch4')
                elif tech == "industrial heat pump high temperature":
                    self.network.add(
                        "Link", name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus0=f"bus_{country}", 
                        bus1=f"bus_{country}_heat")
                elif tech == "OCGT":
                    self.network.add(
                        "Link",  name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus0=f"bus_{country}_ch4",
                        bus1=f"bus_{country}",
                        carrier = 'ch4')
                else:
                    self.network.add(
                        "Generator", name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus=f"bus_{country}",
                        carrier=tech)
                    
    def _add_volatile_generators(self, year:int):
        """
    Add volatile (weather-dependent) generators to the network for a given year.

    Iterates over all configured countries and volatile technologies (e.g. wind,
    solar), adding a capacity-extendable 'Generator' per combination. Capacity
    factors are aligned to network snapshots (missing values filled with 0).

    Args:
        year (int): The simulation year, used to select the appropriate
            capacity factor time series.

    Notes:
        - Capital cost: investment cost plus fixed O&M (FOM) as a fraction of
          investment, in kW terms (not normalized to MW).
        - Marginal cost: variable O&M (VOM) from technology data if available,
          otherwise zero.
        - p_max_pu: per-unit availability profile sourced from capacity factor data.
        - Carrier: set to the technology name for emissions/attribute tracking.
        """
        for country in self.config["countries"]:
            for tech in self.config["technologies_vol"]:
                cf = self.cf[(country, year)]
                if self.config.get("load_year") is not None: # for task b (as we're only using year 2023)
                    cf = cf.iloc[:len(self.network.snapshots)].copy()
                    cf.index = self.network.snapshots
                else:
                    cf = cf.reindex(self.network.snapshots).fillna(0.0) # fill missing values with 0
                self.network.add(
                    "Generator",
                    bus=f"bus_{country}",
                    name=f"generator_vol_{country}_{tech}",
                    p_nom_extendable=True,
                    p_max_pu=cf[tech],
                    marginal_cost=self.tech_data.loc[(tech, "VOM"), "value"] if (tech, "VOM") in self.tech_data.index else 0,
                    capital_cost=self.tech_data.loc[(tech, "investment"), "value"] + self.tech_data.loc[(tech, "investment"), "value"] * (self.tech_data.loc[(tech, "FOM"), "value"]/100),
                    carrier=tech
                )

    def _add_storage(self):
        """
    Add storage units to the network for each country and storage technology.

    Iterates over all configured countries and storage technologies, adding a
    'StorageUnit' component per combination. Each unit is capacity-extendable
    with the following characteristics:

    - Capital cost: derived from technology investment cost plus fixed O&M (FOM),
      both normalized from kW to MW (divided by 1000).
    - Marginal cost: small non-zero value (0.001) to discourage unnecessary dispatch.
    - Marginal cost of storage: zero (no cost for charging).
    - Charge/discharge efficiency: symmetric, sourced from technology data.
    - Standing loss: zero (no self-discharge).
    - Carrier: set to the technology name for emissions/attribute tracking.
        """
        for country in self.config["countries"]:
            for tech in self.config["technologies_storage"]:
                self.network.add(
                    "StorageUnit",
                    bus=f"bus_{country}",
                    name=f"generator_storage_{country}_{tech}", # added country as every component in pypsa needs a unique name,
                    p_nom_extendable=True,
                    marginal_cost=0.001,
                    marginal_cost_storage=0,
                    capital_cost=self.tech_data.loc[(tech, "investment"), "value"] / 1000 + self.tech_data.loc[(tech, "investment"), "value"]/1000 *(self.tech_data.loc[(tech, "FOM"), "value"]/100),
                    efficiency_store=self.tech_data.loc[(tech, "efficiency"), "value"],
                    efficiency_dispatch=self.tech_data.loc[(tech, "efficiency"), "value"],
                    standing_loss=0,
                    carrier=tech
                )

    def _add_transmission_lines(self):
        """
    Add transmission lines and optional methane pipelines to the network.

    Adds AC transmission lines (as 'Line' components) between buses using
    electrical parameters (reactance, nominal apparent power) defined in config.
    Lines are fixed in capacity (not extendable).

    If 'CH4_lines' are specified in the config, also adds methane transport
    links (as 'Link' components) between CH4 buses. These omit reactance
    (irrelevant for gas transport) and are capacity-extendable.
        """
        for line in self.config["transmission_lines"]:
            self.network.add(
                "Line",
                name=line["name"],
                bus0=f"bus_{line['bus0']}",
                bus1=f"bus_{line['bus1']}",
                x=line["x"],
                s_nom=line["s_nom"],
                s_nom_extendable=False,
            )
        if self.config.get("CH4_lines"):
            for line in self.config["CH4_lines"]:
                self.network.add(
                    "Link",
                    name=f"CH4_{line['name']}",
                    bus0=f"bus_{line['bus0']}_ch4",
                    bus1=f"bus_{line['bus1']}_ch4",
                    p_nom_extendable=True,
                )

    def _add_global_co2_limit(self):
        """
    Add a global CO2 emissions constraint to the network.

    Registers a GlobalConstraint named 'CO2Limit' that caps total CO2 emissions
    across all carriers with a 'co2_emissions' attribute, using the limit defined
    in the configuration.
        """
        self.network.add(
            "GlobalConstraint",
            "CO2Limit",
            carrier_attribute="co2_emissions",
            sense="<=",
            constant=self.config["global_CO2_limit"])