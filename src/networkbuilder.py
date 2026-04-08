from src.input import InputHandler
import pypsa


class NetworkBuilder:

    def __init__(self, config, input_data):
        self.config = config
        self.input_data = input_data

    def build(self, year, include_storage=False):
        self.network = pypsa.Network()
        countries = self.config["countries"]
        voltage_level = self.config["voltage_level"]
        self._add_buses(countries, voltage_level)
        self._add_loads(countries, year)
        self._add_conventional_generators(countries)
        self._add_volatile_generators(countries, year)

        if include_storage:
            self._add_storage(countries)

        # if len(countries) > 1:
        # self._add_transmission_lines(transmission_lines, REACTANCE)

        return self.network

    def _add_buses(self, countries, voltage_level):
        for country in countries:
            self.network.add("Bus", name=f"bus_{country}", v_nom=voltage_level)

    def _add_loads(self, countries, year):
        for country in countries:
            demand = self.input_data.load[(country, year)]
            self.network.set_snapshots(demand.index)
            self.network.add(
                "Load",
                name=f"load_{country}",
                bus=f"bus_{country}",
                p_set=demand["Actual Load"],
            )

    def _add_conventional_generators(self, countries):
        for country in countries:
            for tech in self.config["technologies_conv"]:
                self.network.add(
                    "Generator",
                    name=f"generator_conv_{tech}",
                    bus=f"bus_{country}",
                    p_nom_extendable=True,
                    marginal_cost=self.input_data.technology_costs[tech]["vom"],
                    lifetime=self.input_data.technology_costs[tech]['lifetime'],
                    capital_cost=self.input_data.technology_costs[tech]["inv"]+self.input_data.technology_costs[tech]["inv"]*(self.input_data.technology_costs[tech]["fom"]/100),
                )

    def _add_volatile_generators(self, countries, year):
        for country in countries:
            for tech in self.config["technologies_vol"]:
                cf = self.input_data.cf[(country, year)]
                cf = cf.reindex(self.network.snapshots)
                self.network.add(
                    "Generator",
                    bus=f"bus_{country}",
                    name=f"generator_vol_{tech}",
                    p_nom_extendable=True,
                    p_max_pu=cf[tech],
                    marginal_cost=self.input_data.technology_costs[tech]["vom"],
                    capital_cost=self.input_data.technology_costs[tech]["inv"]+self.input_data.technology_costs[tech]["inv"]*(self.input_data.technology_costs[tech]["fom"]/100),
                )

    def _add_storage(self, countries):  # needs some common data for efficiency and standing losses
        for country in countries:
            for tech in self.config["technologies_storage"]:
                self.network.add(
                    "StorageUnit",
                    bus=f"bus_{country}",
                    name=f"generator_storage_{tech}",
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