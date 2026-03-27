from input import InputHandler
import pypsa

class NetworkBuilder:

    def __init__(self, config, input_data):
        self.config = config
        self.input_data = input_data
        self.network = pypsa.Network()


    def build(self, years, include_storage = False, countries = None):
        self.countries = countries

        self._add_buses(countries, VOLTAGE_LEVEL)
        self._add_loads(countries, years)
        self._add_conventional_generators(countries)
        self._add_volatile_generators(countries, years)

        #if include_storage:
            #self._add_storage(countries)

        #if len(countries) > 1:
            #self._add_transmission_lines(transmission_lines, REACTANCE)

    
    def _add_buses(self, countries, VOLTAGE_LEVEL):
        for country in countries:
            self.network.add("Bus", 
                             f'bus_{country}',
                             v_nom = VOLTAGE_LEVEL
                             )

    def _add_loads(self, countries, years):
        for country in countries:
            demand = self.input_data.get_demand(country, years)
            self.network.add('Load',
                             f'load_{country}',
                             bus = f'bus_{country}',
                             p_set = demand['Actual Load']
                             )
            
    def _add_conventional_generators(self, countries):
        for country in countries:
            for tech in self.config['technologies_conv']:
                self.network.add('Generator', 
                                 bus = f'bus_{country}',
                                 p_nom_extendable = True,
                                 marginal_cost = self.config['OPEX'][tech],
                                 capital_cost = self.config['CAPEX'][tech]
                                 )

    def _add_volatile_generators(self, countries, years):
        for country in countries:
            for tech in self.config['technologies_vol']:
                cf = self.input_data.get_cf(country, years)
                self.network.add('Generator', 
                                bus = f'bus_{country}',
                                p_nom_extendable = True,
                                p_max_pu = cf,
                                marginal_cost = self.config['OPEX'][tech],
                                capital_cost = self.config['CAPEX'][tech]
                                )
                
    # def _add_storage(self, countries): #needs some common data for efficiency and standing losses
    #     for country in countries:
    #         self.network.add('StorageUnit',
    #                          bus = f'bus_{country}',
    #                          p_nom_extendable = True,
    #                          marginal_cost = 0,
    #                          marginal_cost_storage = 0,
    #                          capital_cost = self.config['CAPEX']['storage'],
    #                          efficiency_store = 1,
    #                          efficiency_dispatch = 1,
    #                          standing_loss = 0
    #                          )
            
    # def _add_transmission_lines(self, transmission_lines, REACTANCE):
    #     for line in transmission_lines: #should be a dictionary for the lines between countries
    #         self.network.add('Line',
    #                     bus0 = ,
    #                     bus1 = ,
    #                     r_pu = REACTANCE,                       
    #                     )

