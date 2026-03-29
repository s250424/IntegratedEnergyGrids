from src.input import InputHandler
from src.networkbuilder import NetworkBuilder

class Scenario:

    def __init__(self, config, input_data):
        self.config = config
        self.builder = NetworkBuilder(config, input_data)
        self.results = {}

    def run_single_year(self, year):
        network = self.builder.build(year=year)
        network.optimize()
        self.results[year] = network
        return network
    
    def run_multiple_years(self):
        years = self.config['years']
        for year in years:
            self.run_single_year(year=year)
        return self.results
    
    def run_with_storage(self):
        year = self.config['years'][0] # assuming we want to run for the first year in the config, can be modified to loop over years if needed
        network = self.builder.build(year=year, include_storage=True)
        network.optimize()
        return network
    
    def run_multi_countries(self):
        year = self.config['years'][0] # assuming we want to run for the first year in the config, can be modified to loop over years if needed
        network = self.builder.build(year=year)
        network.optimize()
        return network



