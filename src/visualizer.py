import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.lines as mlines
import matplotlib.ticker as mticker
import matplotlib.cm as cm
import numpy as np
import pandas as pd
import pypsa
import os

from requests import patch


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
    
    # CHANGE: modified the names of each technology as their saved with the country code 
    LABEL_MAP = {
        # BE
        "generator_conv_BE_CCGT": "BE CCGT",
        "generator_conv_BE_nuclear": "BE Nuclear",
        "generator_conv_BE_biomass CHP": "BE Biomass CHP",
        "generator_vol_BE_solar-utility": "BE Solar",
        "generator_vol_BE_onwind": "BE Onshore Wind",
        "generator_vol_BE_offwind": "BE Offshore Wind",

        # FR
        "generator_conv_FR_CCGT": "FR CCGT",
        "generator_conv_FR_nuclear": "FR Nuclear",
        "generator_conv_FR_biomass CHP": "FR Biomass CHP",
        "generator_vol_FR_solar-utility": "FR Solar",
        "generator_vol_FR_onwind": "FR Onshore Wind",
        "generator_vol_FR_offwind": "FR Offshore Wind",
        "generator_vol_FR_hydro": "FR Hydro",

        # NL
        "generator_conv_NL_CCGT": "NL CCGT",
        "generator_conv_NL_coal": "NL Coal",
        "generator_conv_NL_oil": "NL Oil",
        "generator_conv_NL_biomass CHP": "NL Biomass CHP",
        "generator_vol_NL_solar-utility": "NL Solar",
        "generator_vol_NL_onwind": "NL Onshore Wind",
        "generator_vol_NL_offwind": "NL Offshore Wind",
        "generator_vol_NL_hydro": "NL Hydro",

        # DE_LU
        "generator_conv_DE_LU_CCGT": "DE/LU CCGT",
        "generator_conv_DE_LU_coal": "DE/LU Coal",
        "generator_conv_DE_LU_oil": "DE/LU Oil",
        "generator_conv_DE_LU_biomass CHP": "DE/LU Biomass CHP",
        "generator_vol_DE_LU_solar-utility": "DE/LU Solar",
        "generator_vol_DE_LU_onwind": "DE/LU Onshore Wind",
        "generator_vol_DE_LU_offwind": "DE/LU Offshore Wind",
        "generator_vol_DE_LU_hydro": "DE/LU Hydro",
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
        Plot and save a stacked bar chart of the annual electricity mix.

        Computes each technology's total dispatched energy and visualises it
        as a single stacked horizontal bar saved to 'results/annual_electricity_mix.png'.
        Segments wide enough show their label inline; narrow segments get an
        annotated leader line above the bar.

        Parameters
        ----------
        dispatch_series_dict : dict[str, pd.Series]
            Mapping of technology name to its hourly dispatch time series.
            Values should be in consistent energy units (e.g. MWh per hour).
        """
        # compute per-technology totals and overall total
        totals_dict = {k: v.sum() for k, v in self.dispatch_series_dict.items()}
        totals_dict = {k: v for k, v in totals_dict.items() if v > 0}
        total_dispatch = sum(totals_dict.values())
    

        # sort descending so largest segment starts from the left
        totals_dict = dict(
            sorted(totals_dict.items(), key=lambda x: x[1], reverse=True)
        )

        LABEL_MAP = {
            "generator_conv_BE_CCGT": "CCGT",
            "generator_conv_BE_nuclear": "Nuclear",
            "generator_conv_BE_biomass CHP": "Biomass CHP",
            "generator_vol_BE_solar-rooftop": "Solar",
            "generator_vol_BE_onwind": "Onshore Wind",
            "generator_vol_BE_offwind": "Offshore Wind",
        }
        
        labels = [LABEL_MAP.get(k, k) for k in totals_dict.keys()]
        values = np.array(list(totals_dict.values()))          # raw MWh
        pct    = values / total_dispatch * 100                 # % for width
        colors = [cm.tab10(i / len(labels)) for i in range(len(labels))]
        print("keys in dict:", list(totals_dict.keys()))
        print("mapped labels:", labels)


        fig, ax = plt.subplots(figsize=(12, 3))

        INLINE_THRESHOLD = 8   # % of total bar width — narrower → outside label
        BAR_Y            = 0
        BAR_HEIGHT       = 0.5
        LABEL_Y_ABOVE    = BAR_Y + BAR_HEIGHT / 2 + 0.30   # base y for outside labels

        # stagger every other narrow label a bit higher to reduce overlap
        stagger_offsets  = [0.0, 0.18]

        left        = 0.0
        bars        = []
        outside_ann = []   # collect (mid_x, label_str) for narrow segments

        for i, (label, value, p, color) in enumerate(zip(labels, values, pct, colors)):
            bar = ax.barh(
                BAR_Y, p, left=left,
                height=BAR_HEIGHT,
                color=color,
                edgecolor="white",
                linewidth=1.2,
            )
            bars.append(bar)

            mid_x = left + p / 2

            if p >= INLINE_THRESHOLD:
                # --- inline label ---
                ax.text(
                    mid_x, BAR_Y,
                    f"{label}\n{value/1000000:,.2f} TWh",
                    va="center", ha="center",
                    fontsize=8, color="white", fontweight="bold",
                )
            else:
                outside_ann.append((mid_x, label, value))

            left += p

        # --- outside labels with leader lines, staggered to reduce overlap ---
        for idx, (mid_x, label, value) in enumerate(outside_ann):
            y_offset  = stagger_offsets[idx % len(stagger_offsets)]
            label_y   = LABEL_Y_ABOVE + y_offset

            ax.annotate(
                f"{label}: {value/1000000:,.2f} TWh",
                xy        =(mid_x, BAR_Y + BAR_HEIGHT / 2),   # tip of arrow → bar edge
                xytext    =(mid_x, label_y),                   # label position
                ha        ="center", va="bottom",
                fontsize  =8,
                arrowprops=dict(
                    arrowstyle="-",          # plain line, no arrowhead
                    color="black",
                    lw=0.8,
                ),
            )

        # total label to the right of the bar
        ax.text(
            101, BAR_Y,
            f"Total: {total_dispatch/1000000:,.2f} TWh",
            va="center", ha="left",
            fontsize=9, fontstyle="italic",
        )

        ax.set_xlim(0, 100)
        ax.set_ylim(-0.6, 1.2)        # extra headroom for staggered labels
        ax.set_xlabel("Share of Total Dispatch (%)")
        ax.set_yticks([])
        ax.spines[["top", "right", "left"]].set_visible(False)

        # legend below the chart
        ax.legend(
            handles=[b[0] for b in bars],
            labels=labels,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.35),
            ncol=min(len(labels), 4),
            frameon=False,
            fontsize=9,
        )

        fig.tight_layout()
        plt.savefig(f"results/{name}.png", dpi=150, bbox_inches="tight")

    
    def plot_sensitivity_capacity_to_weather_years(self, name="sensitivity_capacity_to_weather_years") -> None:
        """
        Plot and save a box plot of optimal capacity per technology across weather years.

        For each technology in `self.capacity_dict`, the boxplot represents the
        distribution of optimal capacity across weather years, and the error bars extend to the
        min and max values, illustrating the sensitivity to weather year choice.

        Saves the figure to 'results/sensitivity_capacity_to_weather_years.png'.
        """
        labels = [self.LABEL_MAP.get(k, k) for k in self.capacity_dict.keys()]

        data = []
        for v in self.capacity_dict.values():
            if all(val == 0 for val in v):
                data.append([np.nan] * len(v))  # 👈 clave
            else:
                data.append(v)

        fig, ax = plt.subplots(figsize=(9, 5))

        medianprops = dict(color='red', linewidth=1)
        boxprops = dict(linewidth=1.2, color='black')
        whiskerprops = dict(linewidth=1, linestyle='--', color='gray')
        capprops = dict(linewidth=1, color='gray')
        flierprops = dict(marker='o', markersize=4, alpha=0.5, color='gray')

        bp = ax.boxplot(
            data,
            tick_labels=labels,
            patch_artist=True,
            medianprops=medianprops,
            boxprops=boxprops,
            whiskerprops=whiskerprops,
            capprops=capprops,
            flierprops=flierprops
        )

        for patch in bp['boxes']:
            patch.set_facecolor('#DCE6F1')

        ax.set_ylabel("Capacity (MW)")
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", "."))
        )
        ax.tick_params(axis="x", rotation=30)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        fig.tight_layout()
        plt.savefig(
            self._make_path(name),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close()
    
    def plot_capacity_factors(self, input_data, country="BE", name="capacity_factors"):
        """
        Plot capacity factors for different years for each renewable technology.
        """

        available_techs = input_data.cf[(country, input_data.config["years"][0])].columns
        technologies = [tech for tech in ["solar-utility", "onwind", "offwind", "hydro"] if tech in available_techs]

        fig, axes = plt.subplots(len(technologies), 1, figsize=(12, 8), sharex=True)

        for i, tech in enumerate(technologies):
            for year in input_data.config["years"]:
                cf = input_data.cf[(country, year)][tech]

                axes[i].plot(
                cf.index,
                cf.values,
                alpha=0.5,
                linewidth=0.3
            )

                #  monthly mean to see the seasonal pattern more clearly
                monthly_mean = cf.resample("ME").mean()

                axes[i].plot(
                    monthly_mean.index,
                    monthly_mean.values,
                    linewidth=1.8,
                    linestyle="-",
                    label=f"{year} (monthly avg)"
                )
            axes[i].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            axes[i].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
            axes[i].set_ylabel(tech)
            axes[i].set_ylim(0, 1)
            axes[i].grid(alpha=0.3)

        axes[-1].set_xlabel("Time")
        axes[0].legend(title="Year")

        fig.tight_layout()
        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()