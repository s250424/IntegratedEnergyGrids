from src.input import InputHandler
from networkbuilder import NetworkBuilder

class Scenario:

    def __init__(self, config, input_data):
        self.config = config
        self.builder = NetworkBuilder(config, input_data)
        self.results = {}

    def run_single_year(self):
        year = self.config['years'][0]
        network = self.builder.build(years=year)
        network.optimize()
        self.results[year] = network
        return network
    
    def run_multiple_years(self):
        years = self.config['years']
        for year in years:
            self.run_single_year(years=years)
        return self.results
    
    def run_with_storage(self):
        years = self.config['years']
        network = self.builder.build(years=years, include_storage=True)
        network.optimize()
        return network
    
    def run_multi_countries(self, countries):
        years = self.config['years']
        network = self.builder.build(years=years, countries=countries)
        network.optimize()
        return network



