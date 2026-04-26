from src.input import InputHandler
import pypsa


class NetworkBuilder:
    def __init__(self, config, input_data, year):
        # Rename inputs for more convenient use
        self.config = config
        self.load = input_data.load
        self.load_heat = input_data.load_heat
        self.tech_data = input_data.tech_data
        self.cf = input_data.cf
        
        # Build and optimize the network
        self._build_network(year)
        self.network.optimize()

    def _build_network(self, year):
        """>>>> INITIALIZE PYPSA NETWORK <<<<"""
        self.network = pypsa.Network()
        
        """>>>> ADD COMPONENTS TO PYPSA NETWORK <<<<"""
        self._add_buses_carrier_stocks()
        self._add_loads(year)
        self._add_dispatchable_generators()
        self._add_volatile_generators(year)
        if len(self.config["countries"]) > 1:
            self._add_transmission_lines()
        if self.config.get("technologies_storage"):
            self._add_storage()
        if self.config.get("global_CO2_limit"):
            self._add_global_co2_limit()

    def _add_buses_carrier_stocks(self):
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
        self.network.add("Carrier", "heat")
        self.network.add("Carrier", "biomass", co2_emissions=self.tech_data.loc[("solid biomass", "CO2 intensity"), "value"])   # t CO2/MWh

        # dispatchable without stock & busses
        self.network.add("Carrier", "coal", co2_emissions=self.tech_data.loc[("coal", "CO2 intensity"), "value"])   # t CO2/MWh
        self.network.add("Carrier", "nuclear", co2_emissions=0.012) # t CO2/MWh, from Claude

        # volatile
        self.network.add("Carrier", "solar", co2_emissions=0.043)   # t CO2/MWh, from Claude
        self.network.add("Carrier", "offwind", co2_emissions=0.012) # t CO2/MWh, from Claude
        self.network.add("Carrier", "onwind", co2_emissions=0.011)  # t CO2/MWh, from Claude

    def _add_loads(self, year):
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
                heating_demand = self.load_heat[(country, year)]  # TODO still needs to be added in InputHandler
                self.network.add(
                    "Load",
                    name=f"load_{country}_heat",
                    bus=f"bus_{country}_heat",
                    p_set=heating_demand["Actual Load"],
                )

    def _add_dispatchable_generators(self):
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
                        efficiency2=self.tech_data.loc[(tech, "efficiency-heat"), "value"])
                elif tech == "CCGT":
                    self.network.add(
                        "Link", name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus0=f"bus_{country}_ch4", 
                        bus1=f"bus_{country}",
                        bus2=f"bus_{country}_heat",
                        efficiency2=self.tech_data.loc[(tech, "efficiency"), "value"])     # TODO add heat efficiency                
                elif tech == "gas boiler steam":
                    self.network.add(
                        "Link", name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus0=f"bus_{country}_ch4", 
                        bus1=f"bus_{country}_heat")
                elif tech == "industrial heat pump high temperature":
                    self.network.add(
                        "Link", name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus0=f"bus_{country}", 
                        bus1=f"bus_{country}_heat")
                elif tech == "OCGT":
                    self.network.add(
                        "Link",  name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus0=f"bus_{country}_ch4",
                        bus1=f"bus_{country}")
                else:
                    self.network.add(
                        "Generator", name=name, p_nom_extendable=True, marginal_cost=marginal_cost, lifetime=lifetime, capital_cost=capital_cost, efficiency=efficiency,
                        bus=f"bus_{country}",
                        carrier=tech)
                    
    def _add_volatile_generators(self, year):
        for country in self.config["countries"]:
            for tech in self.config["technologies_vol"]:
                cf = self.cf[(country, year)]
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

    def _add_storage(self):  # needs some common data for efficiency and standing losses
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
                    name=line["name"],
                    bus0=f"bus_{line['bus0']}_ch4",
                    bus1=f"bus_{line['bus1']}_ch4",
                    x=line["x"],
                    s_nom_extendable=True,
                )

    def _add_global_co2_limit(self):
        self.network.add(
            "GlobalConstraint",
            "CO2Limit",
            carrier_attribute="CO2_emissions",
            sense="<=",
            constant=self.config["global_CO2_limit"])