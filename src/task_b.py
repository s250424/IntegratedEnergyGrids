from task_a_test import NetworkBuilder
from visualizer import Visualizer

class ScenarioRunner:
    """
    Run sensitivity analysis for different years
    """
    def __init__(self, weather_years: list[int]):
        self.years = weather_years
    
    def run_weather_sensitivity(self) -> dict[str, list[float]]:
        capacity_dict = {}

        for year in self.years:
            print(f"Running model for weather year {year}")

            builder = NetworkBuilder(weather_year=year)
            n = builder.build()

            n.optimize()

            capacities = n.generators.p_nom_opt

            for tech in capacities.index:
                if tech not in capacity_dict:
                    capacity_dict[tech] = []
                capacity_dict[tech].append(capacities[tech])
        return capacity_dict

if __name__ == "__main__":
    years = [2020]

    runner = ScenarioRunner(years)
    capacity_dict = runner.run_weather_sensitivity()

    print("\nCapacity results:")
    print(capacity_dict)

    viz = Visualizer(dispatch_series_dict={}, capacity_dict=capacity_dict)
    viz.plot_sensitivity_capacity_to_weather_years()