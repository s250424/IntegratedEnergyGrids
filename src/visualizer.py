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
        self.network = n
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
                    series.values / 1000,  # Convert MWh to GWh
                    label=self.LABEL_MAP.get(label, label),
                    color=color,
                    linewidth=1.4,
                    alpha=0.9,
                )
            axes[idx].set_ylabel("Dispatch (GWh)", fontsize=13)  # CHANGED: MWh -> GWh
            axes[idx].set_xlabel("")
            axes[idx].set_title(season_labels[idx], fontsize=13)  # CHANGED: added subplot titles
            axes[idx].set_ylim(0, y_max * 1.1 / 1000)                   # CHANGED: convert to GWh
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
        If multiple countries are present, one horizontal bar per country is drawn
        vertically, with consistent technology colours and a single shared legend.
        """
        # --- gather data per country ---
        # group dispatch keys by country (key format: generator_xxx_COUNTRY_tech)
        country_totals = {}  # {country: {key: total_MWh}}
        for k, v in self.dispatch_series_dict.items():
            total = v.sum()
            if total <= 0:
                continue
            # extract country from key, e.g. "generator_conv_BE_CCGT" → "BE"
            parts = k.split("_")
            # country is the part after "conv" or "vol" or "storage"
            try:
                type_idx = next(i for i, p in enumerate(parts) if p in ("conv", "vol", "storage"))
                country = parts[type_idx + 1]
            except StopIteration:
                country = "unknown"

            if country not in country_totals:
                country_totals[country] = {}
            country_totals[country][k] = total

        countries = list(country_totals.keys())

        # --- build a global colour map keyed by technology label ---
        # collect all unique labels across all countries
        all_keys = sorted({k for c in country_totals.values() for k in c.keys()})
        all_labels = [self.LABEL_MAP.get(k, k) for k in all_keys]
        label_to_color = {
            label: cm.tab10(i / len(all_labels))
            for i, label in enumerate(all_labels)
        }

        # --- layout ---
        n_countries   = len(countries)
        BAR_HEIGHT    = 0.5
        BAR_SPACING   = 1.0          # vertical distance between bar centres
        INLINE_THRESHOLD = 8         # % width below which label goes outside
        stagger_offsets  = [0.0, 0.18]

        fig_height = max(3, n_countries * 1.8 + 1.5)
        fig, ax = plt.subplots(figsize=(12, fig_height))

        legend_handles = {}          # label → patch, for the shared legend
        all_outside    = []          # (mid_x, label, value, bar_y) across all bars

        for c_idx, country in enumerate(countries):
            bar_y      = c_idx * BAR_SPACING
            totals     = country_totals[country]
            total_disp = sum(totals.values())

            # sort descending
            totals = dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))

            left = 0.0
            for key, value in totals.items():
                label = self.LABEL_MAP.get(key, key)
                color = label_to_color[label]
                pct   = value / total_disp * 100

                bar = ax.barh(
                    bar_y, pct, left=left,
                    height=BAR_HEIGHT,
                    color=color,
                    edgecolor="white",
                    linewidth=1.2,
                )

                # collect for legend (only need one patch per label)
                if label not in legend_handles:
                    legend_handles[label] = bar[0]

                mid_x = left + pct / 2

                if pct >= INLINE_THRESHOLD:
                    ax.text(
                        mid_x, bar_y,
                        f"{label}\n{value/1e6:,.2f} TWh",
                        va="center", ha="center",
                        fontsize=7.5, color="white", fontweight="bold",
                    )
                else:
                    all_outside.append((mid_x, label, value, bar_y))

                left += pct

            # total label to the right of each bar
            ax.text(
                101, bar_y,
                f"Total: {total_disp/1e6:,.2f} TWh",
                va="center", ha="left",
                fontsize=8.5, fontstyle="italic",
            )

        # --- outside labels with leader lines ---
        # group by bar_y so stagger offsets reset per country
        from itertools import groupby
        all_outside_sorted = sorted(all_outside, key=lambda x: x[3])
        for bar_y, group in groupby(all_outside_sorted, key=lambda x: x[3]):
            for idx, (mid_x, label, value, _) in enumerate(group):
                y_offset = stagger_offsets[idx % len(stagger_offsets)]
                label_y  = bar_y + BAR_HEIGHT / 2 + 0.18 + y_offset
                ax.annotate(
                    f"{label}: {value/1e6:,.2f} TWh",
                    xy        =(mid_x, bar_y + BAR_HEIGHT / 2),
                    xytext    =(mid_x, label_y),
                    ha        ="center", va="bottom",
                    fontsize  =7.5,
                    arrowprops=dict(arrowstyle="-", color="black", lw=0.8),
                )

        # --- axes formatting ---
        ax.set_xlim(0, 100)
        ax.set_ylim(
            -BAR_HEIGHT,
            (n_countries - 1) * BAR_SPACING + BAR_HEIGHT + 0.8,  # headroom for labels
        )
        ax.set_yticks([c * BAR_SPACING for c in range(n_countries)])
        ax.set_yticklabels(countries, fontsize=11)
        ax.set_xlabel("Share of Total Dispatch (%)")
        ax.spines[["top", "right", "left"]].set_visible(False)

        # --- single shared legend ---
        ax.legend(
            handles=list(legend_handles.values()),
            labels=list(legend_handles.keys()),
            loc="upper center",
            bbox_to_anchor=(0.5, -0.15),
            ncol=min(len(legend_handles), 4),
            frameon=False,
            fontsize=9,
        )

        fig.tight_layout()
        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()

    
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
        label_tech_map = {
            "solar-utility": "Solar",  
            "onwind": "Onshore Wind",
            "offwind": "Offshore Wind",
            "hydro": "Hydro",
        }

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
            axes[i].set_ylabel(label_tech_map.get(tech, tech))
            axes[i].set_ylim(0, 1)
            axes[i].grid(alpha=0.3)

        axes[-1].set_xlabel("Time")
        axes[0].legend(title="Year")

        fig.tight_layout()
        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()

    def plot_dispatch_diff_time_series(
        self,
        other: "Visualizer",
        start_summer: pd.Timestamp,
        start_winter: pd.Timestamp,
        name: str = "dispatch_diff_c_minus_a",
        ) -> None:
        """
        Plot the difference in dispatch time series (self - other) for a summer
        and winter week. Intended to compare scenario C (self) against scenario A
        (other). Positive values mean more dispatch in self, negative means less.

        Parameters
        ----------
        other : Visualizer
            The baseline visualizer (scenario A) to subtract from.
        start_summer : pd.Timestamp
            Start of the summer week (inclusive).
        start_winter : pd.Timestamp
            Start of the winter week (inclusive).
        """
        end_summer = start_summer + pd.Timedelta(days=7)
        end_winter = start_winter + pd.Timedelta(days=7)

        # union of all technology keys across both scenarios
        all_keys = sorted(
            set(self.dispatch_series_dict.keys()) | set(other.dispatch_series_dict.keys())
        )
        colors = [cm.tab10(i / len(all_keys)) for i in range(len(all_keys))]

        def compute_diff(key, start, end):
            """Return (C_series - A_series) for a given key and time window."""
            s_self  = self.dispatch_series_dict.get(key)
            s_other = other.dispatch_series_dict.get(key)

            if s_self is not None:
                s_self  = s_self.loc[start:end]
            if s_other is not None:
                s_other = s_other.loc[start:end]

            if s_self is None:
                return -s_other                        # only in A → fully negative
            if s_other is None:
                return s_self                          # only in C → fully positive
            return s_self - s_other                    # both exist → difference

        fig, axes = plt.subplots(
            nrows=2, ncols=1, figsize=(14, 7), sharex=False, constrained_layout=True
        )

        season_params = [
            ("Summer", start_summer, end_summer),
            ("Winter", start_winter, end_winter),
        ]

        # compute y_max across both seasons for consistent scaling
        y_abs_max = 0
        for _, start, end in season_params:
            for key in all_keys:
                diff = compute_diff(key, start, end)
                y_abs_max = max(y_abs_max, diff.abs().max())

        for idx, (season_label, start, end) in enumerate(season_params):
            ax = axes[idx]

            for key, color in zip(all_keys, colors):
                diff = compute_diff(key, start, end)
                ax.plot(
                    diff.index,
                    diff.values / 1000,          # MWh → GWh
                    label=self.LABEL_MAP.get(key, key),
                    color=color,
                    linewidth=1.4,
                    alpha=0.9,
                )

            # zero reference line
            ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)

            ax.set_title(season_label, fontsize=13)
            ax.set_ylabel("Dispatch difference (GWh)\nC − A", fontsize=12)
            ax.set_ylim(-y_abs_max * 1.1 / 1000, y_abs_max * 1.1 / 1000)
            ax.tick_params(axis="both", labelsize=12)
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            ax.grid(axis="x", linestyle=":", alpha=0.3)

            ax.xaxis.set_major_locator(mdates.DayLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%a\n%d %b"))
            ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
            ax.set_xlim(diff.index[0], diff.index[-1])
            ax.spines[["top", "right"]].set_visible(False)

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles, labels,
            loc="lower center", ncol=len(handles),
            fontsize=12, framealpha=0.7, bbox_to_anchor=(0.5, -0.08),
        )

        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()
    
    def plot_storage_behavior(
        self,
        start_summer: pd.Timestamp,
        start_winter: pd.Timestamp,
        name: str = "storage_behavior",
    ) -> None:
        """
        Plot storage power (charge/discharge) and state of charge for a summer
        and winter week.

        Each season gets two stacked subpanels:
        - Top: power in GW (positive = discharging, negative = charging)
        - Bottom: state of charge in GWh

        Parameters
        ----------
        start_summer : pd.Timestamp
            Start of the summer week (inclusive).
        start_winter : pd.Timestamp
            Start of the winter week (inclusive).
        """
        storage_units = self.network.storage_units.index.tolist()

        if not storage_units:
            print("No storage units found in network — skipping plot.")
            return

        colors = [cm.tab10(i / len(storage_units)) for i in range(len(storage_units))]

        end_summer = start_summer + pd.Timedelta(days=7)
        end_winter = start_winter + pd.Timedelta(days=7)

        season_params = [
            ("Summer", start_summer, end_summer),
            ("Winter", start_winter, end_winter),
        ]

        # 2 seasons × 2 subpanels (power + soc) = 4 rows
        fig, axes = plt.subplots(
            nrows=4, ncols=1, figsize=(14, 12), constrained_layout=True
        )

        # row index mapping: season 0 → rows 0,1 / season 1 → rows 2,3
        for s_idx, (season_label, start, end) in enumerate(season_params):
            ax_power = axes[s_idx * 2]
            ax_soc   = axes[s_idx * 2 + 1]

            for unit, color in zip(storage_units, colors):
                label = self.LABEL_MAP.get(unit, unit)

                # --- power ---
                power = self.network.storage_units_t.p[unit].loc[start:end]
                ax_power.plot(
                    power.index,
                    power.values / 1000,        # MW → GW
                    label=label,
                    color=color,
                    linewidth=1.4,
                    alpha=0.9,
                )

                # --- state of charge ---
                soc = self.network.storage_units_t.state_of_charge[unit].loc[start:end]
                ax_soc.plot(
                    soc.index,
                    soc.values / 1000,          # MWh → GWh
                    label=label,
                    color=color,
                    linewidth=1.4,
                    alpha=0.9,
                )

            # --- power panel formatting ---
            ax_power.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
            ax_power.set_title(season_label, fontsize=13)
            ax_power.set_ylabel("Power (GW)\n+ discharge / − charge", fontsize=11)
            ax_power.grid(axis="y", linestyle="--", alpha=0.4)
            ax_power.grid(axis="x", linestyle=":", alpha=0.3)
            ax_power.spines[["top", "right"]].set_visible(False)
            ax_power.tick_params(axis="both", labelsize=11)

            # --- soc panel formatting ---
            ax_soc.set_ylabel("State of Charge (GWh)", fontsize=11)
            ax_soc.set_ylim(bottom=0)
            ax_soc.grid(axis="y", linestyle="--", alpha=0.4)
            ax_soc.grid(axis="x", linestyle=":", alpha=0.3)
            ax_soc.spines[["top", "right"]].set_visible(False)
            ax_soc.tick_params(axis="both", labelsize=11)

            # shared x-axis formatting for both panels in this season
            for ax in [ax_power, ax_soc]:
                ax.xaxis.set_major_locator(mdates.DayLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%a\n%d %b"))
                ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
                ax.set_xlim(start, end)

        # single shared legend at the bottom
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles, labels,
            loc="lower center", ncol=len(handles),
            fontsize=12, framealpha=0.7, bbox_to_anchor=(0.5, -0.04),
        )

        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()