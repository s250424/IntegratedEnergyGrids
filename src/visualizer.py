import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.cm as cm
import numpy as np
import pandas as pd
import pypsa
import os


class Visualizer:
    def __init__(self, n: pypsa.Network, scenario_name: str = ""):
        dispatch_series_dict = {}
        capacity_dict = {}
        print(n.generators.index)
        for gen in n.generators.index:
            dispatch_series_dict[gen] = n.generators_t.p[gen]
            capacity_dict[gen] = n.generators.loc[gen, "p_nom_opt"]
        self.dispatch_series_dict = dispatch_series_dict
        self.capacity_dict = capacity_dict
        self.scenario_name = scenario_name

    def _make_path(self, default_name: str) -> str:
        if self.scenario_name:
            prefix = self.scenario_name + "_"
        else:
            prefix = ""
        os.makedirs("results", exist_ok=True)
        return f"results/{prefix}{default_name}.png"
    
    LABEL_MAP = {
    "generator_conv_CCGT": "CCGT",
    "generator_conv_nuclear": "Nuclear",
    "generator_conv_biomass CHP": "Biomass CHP",
    "generator_vol_solar-rooftop": "Solar",
    "generator_vol_onwind": "Onshore Wind",
    "generator_vol_offwind": "Offshore Wind",
}


    def plot_dispatch_time_series(
        self,
        start_summer: pd.Timestamp,
        start_winter: pd.Timestamp,
        name = "dispatch_summer_winter"
    ) -> None:
        """
        Plot dispatch time series for a summer and winter week.

        Filters each series to a 7-day window starting at the given timestamps
        and produces a two-panel figure (summer on top, winter below).
        The figure is saved to 'results/dispatch_summer_winter.png'.

        Parameters
        ----------
        dispatch_series_dict : dict[str, pd.Series]
            Mapping of dispatch-source label to a time-indexed pd.Series
            (e.g. {"Solar": ..., "Wind": ...}). All series must share the
            same DatetimeIndex frequency and cover both week windows.
        start_summer : pd.Timestamp
            Start of the summer week (inclusive).
        start_winter : pd.Timestamp
            Start of the winter week (inclusive).
        """
        colors = [
            cm.tab10(i / len(self.dispatch_series_dict))
            for i in range(len(self.dispatch_series_dict))
        ]  # create colors dynamically
        end_summer = start_summer + pd.Timedelta(days=7)
        end_winter = start_winter + pd.Timedelta(days=7)

        # filter dispatch series based on the desired week
        summer_dict = {
            label: series.loc[start_summer:end_summer]
            for label, series in self.dispatch_series_dict.items()
        }
        winter_dict = {
            label: series.loc[start_winter:end_winter]
            for label, series in self.dispatch_series_dict.items()
        }

        # create axes so that summer dispatch and winter dispatch are plotted next to each other
        fig, axes = plt.subplots(
            nrows=2, ncols=1, figsize=(14, 7), sharex=False, constrained_layout=True
        )

        # create y_max to scale both y-axis the same
        y_max = 0
        for season_dict in [summer_dict, winter_dict]:
            for series in season_dict.values():
                y_max = max(y_max, series.max())

        season_labels = ["Summer", "Winter"]

        # plot the dispatch series
        for idx, season_dict in enumerate([summer_dict, winter_dict]):
            for (label, series), color in zip(season_dict.items(), colors):
                axes[idx].plot(
                    series.index,
                    series.values,
                    label=self.LABEL_MAP.get(label, label),
                    color=color,
                    linewidth=1.4,
                    alpha=0.9,
                )
            axes[idx].set_ylabel("Dispatch (MWh)", fontsize=13)  # CHANGED: fontsize 10 -> 13
            axes[idx].set_xlabel("")
            axes[idx].set_title(season_labels[idx], fontsize=13)  # CHANGED: added subplot titles
            axes[idx].set_ylim(0, y_max * 1.1)                   # CHANGED: added shared y axis limit
            axes[idx].tick_params(axis="both", labelsize=12)      # CHANGED: added tick label fontsize
            axes[idx].grid(axis="y", linestyle="--", alpha=0.4)
            axes[idx].grid(axis="x", linestyle=":", alpha=0.3)

            axes[idx].xaxis.set_major_locator(mdates.DayLocator())
            axes[idx].xaxis.set_major_formatter(mdates.DateFormatter("%a\n%d %b"))
            axes[idx].xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))

            axes[idx].set_xlim(series.index[0], series.index[-1])
            axes[idx].spines[["top", "right"]].set_visible(False)

            # CHANGED: removed per-subplot legend from here

        # CHANGED: replaced per-subplot legend with single shared figure legend
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=len(handles),
                fontsize=12, framealpha=0.7, bbox_to_anchor=(0.5, -0.08))

        plt.savefig(self._make_path("dispatch_summer_winter"), dpi=150, bbox_inches="tight")
        plt.close()

    def plot_annual_electricity_mix(self, name="annual_electricity_mix") -> None:
        """
        Plot and save a pie chart of the annual electricity mix.

        Computes each technology's share of total dispatched energy and
        visualises it as a pie chart saved to 'results/annual_electricity_mix.png'.

        Parameters
        ----------
        dispatch_series_dict : dict[str, pd.Series]
            Mapping of technology name to its hourly dispatch time series.
            Values should be in consistent energy units (e.g. MWh per hour).
        """
        colors = [
            cm.tab10(i / len(self.dispatch_series_dict))
            for i in range(len(self.dispatch_series_dict))
        ]  # create colors dynamically

        # obtain the contribution of each technology to total dispatch
        total_dispatch = sum(s.sum() for s in self.dispatch_series_dict.values())
        contribution_dict = {
            k: v.sum() / total_dispatch for k, v in self.dispatch_series_dict.items()
        }

        # create pie plot
        labels = list(contribution_dict.keys())
        values = np.array(list(contribution_dict.values())) * 100  # → %

        fig, ax = plt.subplots(figsize=(7, 7))
        wedges, _, autotexts = ax.pie(
            values,
            labels=labels,
            colors=colors,
            autopct=lambda p: f"{p:.1f}%" if p > 2 else "",
            startangle=90,
            wedgeprops=dict(linewidth=1.2, edgecolor="white"),
        )
        for at in autotexts:
            at.set_fontsize(10)

        fig.tight_layout()
        plt.savefig(f"results/{name}.png", dpi=150, bbox_inches="tight")

    def plot_sensitivity_capacity_to_weather_years(self, name="sensitivity_capacity_to_weather_years") -> None:
        """
        Plot and save a bar chart of optimal capacity per technology across weather years.

        For each technology in `self.capacity_dict`, the bar height represents the
        mean optimal capacity across weather years, and the error bars extend to the
        min and max values, illustrating the sensitivity to weather year choice.

        Saves the figure to 'results/sensitivity_capacity_to_weather_years.png'.
        """
        colors = [
            cm.tab10(i / len(self.capacity_dict))
            for i in range(len(self.capacity_dict))
        ]  # create colors dynamically

        # obtain average capacity and variability
        capacity_dict_statistics = {
            k: {"mean": np.mean(v), "min": np.min(v), "max": np.max(v)}
            for k, v in self.capacity_dict.items()
        }

        # create the plot
        labels = list(capacity_dict_statistics.keys())
        means = [capacity_dict_statistics[k]["mean"] for k in labels]
        lower = [
            capacity_dict_statistics[k]["mean"] - capacity_dict_statistics[k]["min"]
            for k in labels
        ]  # downward
        upper = [
            capacity_dict_statistics[k]["max"] - capacity_dict_statistics[k]["mean"]
            for k in labels
        ]  # upward

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(labels, means, color=colors, edgecolor="white", linewidth=0.8)
        ax.errorbar(
            labels,
            means,
            yerr=[lower, upper],
            fmt="black",
            color=colors,
            capsize=6,
            linewidth=1.5,
        )

        ax.set_ylabel("Capacity")
        ax.tick_params(axis="x", rotation=30)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        plt.savefig(
            f"results/{name}.png",
            dpi=150,
            bbox_inches="tight",
        )
