from src.input import InputHandler
import pypsa


class NetworkBuilder:

    def __init__(self, config, input_data, year):
        self.config = config
        self.input_data = input_data
        self.network = self._build_network(year)
        self.network.optimize()

    def _build_network(self, year):
        """>>>> INITIALIZE PYPSA NETWORK <<<<"""
        self.network = pypsa.Network()
        
        """>>>> ADD COMPONENTS TO PYPSA NETWORK <<<<"""
        self._add_buses()
        self._add_carrier_init()
        self._add_loads(year)
        self._add_conventional_generators()
        self._add_volatile_generators(year)
        if len(self.config["countries"]) > 1:
            self._add_transmission_lines()
        if self.config.get("technologies_storage"):
            self._add_storage()
        if self.config.get("global_CO2_limit"):
            self._add_global_co2_limit()
        return self.network

    def _add_buses(self):
        for country in self.config["countries"]:
            self.network.add("Bus", name=f"bus_{country}", v_nom=self.config["voltage_level"], carrier="electricity")
            self.network.add("Bus", name=f"bus_{country}_heat", carrier="heat")
            self.network.add("Bus", name=f"bus_{country}_ch4", carrier="ch4")

    def _add_carrier_init(self):
        # TODO define carriers and link carrier to CO2 emission
        for country in self.config["countries"]:
            if self.config.get("CH4_lines"):
                if country == "NL":
                    self.network.add("Store", f"gas_stock_{country}", e_initial=1e20, e_nom=1e20, bus=f"bus_{country}_ch4") 
            else:
                self.network.add("Store", f"gas_stock_{country}", e_initial=1e20, e_nom=1e20, bus=f"bus_{country}_ch4") 

    def _add_loads(self, year):
        for country in self.config["countries"]:
            demand = self.input_data.load[(country, year)]
            self.network.set_snapshots(demand.index)
            self.network.add(
                "Load",
                name=f"load_{country}",
                bus=f"bus_{country}",
                p_set=demand["Actual Load"],
            )
            if self.config.get("include_heat"):
                heating_demand = self.input_data.heating_load[(country, year)]  # TODO still needs to be added in InputHandler
                self.network.add(
                    "Load",
                    name=f"load_{country}_heat",
                    bus=f"bus_{country}_heat",
                    p_set=heating_demand["Actual Load"],
                )

    def _add_conventional_generators(self): # TODO add carrier to conventional generator
        for country in self.config["countries"]:
            for tech in self.config["technologies_conv"][country]:
                if tech == "OCGT":
                    self.network.add(
                        "Link", 
                        "OCGT", 
                        bus0=f"bus_{country}_ch4", 
                        bus1=f"bus_{country}",
                        p_nom_extendable=True, 
                        marginal_cost=self.input_data.technology_costs[tech]["vom"],
                        lifetime=self.input_data.technology_costs[tech]['lifetime'],
                        capital_cost=self.input_data.technology_costs[tech]["inv"]+self.input_data.technology_costs[tech]["inv"]*(self.input_data.technology_costs[tech]["fom"]/100),
                        efficiency=0.35)    # TODO add efficiency from input_data
                elif tech == "gas_boiler":  # TODO find correct name for gas boiler
                    self.network.add(
                        "Link",
                        name=f"generator_conv_{country}_{tech}",   
                        bus0=f"bus_{country}_ch4", 
                        bus1=f"bus_{country}_heat", 
                        p_nom_extendable=True, 
                        marginal_cost=self.input_data.technology_costs[tech]["vom"],
                        lifetime=self.input_data.technology_costs[tech]['lifetime'],
                        capital_cost=self.input_data.technology_costs[tech]["inv"]+self.input_data.technology_costs[tech]["inv"]*(self.input_data.technology_costs[tech]["fom"]/100),
                        efficiency=0.9)     # TODO add efficiency from input_data
                elif tech == "CHP":         # TODO find correct name for CHP
                    self.network.add(
                        "Link",
                        name=f"generator_conv_{country}_{tech}",   
                        bus0=f"bus_{country}_ch4", 
                        bus1=f"bus_{country}",
                        bus2=f"bus_{country}_heat",
                        p_nom_extendable=True, 
                        marginal_cost=self.input_data.technology_costs[tech]["vom"],
                        lifetime=self.input_data.technology_costs[tech]['lifetime'],
                        capital_cost=self.input_data.technology_costs[tech]["inv"]+self.input_data.technology_costs[tech]["inv"]*(self.input_data.technology_costs[tech]["fom"]/100),
                        efficiency=0.3,
                        efficiency2=0.3)     # TODO add efficiency from input_data
                else:
                    self.network.add(
                        "Generator",
                        name=f"generator_conv_{country}_{tech}", # added country as every component in pypsa needs a unique name,
                        bus=f"bus_{country}",
                        p_nom_extendable=True,
                        marginal_cost=self.input_data.technology_costs[tech]["vom"],
                        lifetime=self.input_data.technology_costs[tech]['lifetime'],
                        capital_cost=self.input_data.technology_costs[tech]["inv"]+self.input_data.technology_costs[tech]["inv"]*(self.input_data.technology_costs[tech]["fom"]/100),
                    )

    def _add_volatile_generators(self, year):
        for country in self.config["countries"]:
            for tech in self.config["technologies_vol"][country]:
                cf = self.input_data.cf[(country, year)]
                cf = cf.reindex(self.network.snapshots).fillna(0.0) # fill missing values with 0
                self.network.add(
                    "Generator",
                    bus=f"bus_{country}",
                    name=f"generator_vol_{country}_{tech}", # added country as every component in pypsa needs a unique name,
                    p_nom_extendable=True,
                    p_max_pu=cf[tech],
                    marginal_cost=self.input_data.technology_costs[tech]["vom"],
                    capital_cost=self.input_data.technology_costs[tech]["inv"]+self.input_data.technology_costs[tech]["inv"]*(self.input_data.technology_costs[tech]["fom"]/100),
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
                    capital_cost=self.input_data.technology_costs[tech]["inv"]+self.input_data.technology_costs[tech]["inv"]*(self.input_data.technology_costs[tech]["fom"]/100),
                    efficiency_store=self.input_data.technology_costs[tech]["efficiency"],
                    efficiency_dispatch=self.input_data.technology_costs[tech]["efficiency"],
                    standing_loss=0,
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