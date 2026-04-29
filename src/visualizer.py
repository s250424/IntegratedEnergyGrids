import os

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.lines as mlines
import matplotlib.ticker as mticker
import matplotlib.cm as cm
import numpy as np
import pandas as pd
import pypsa

class Visualizer:
    """Visualizing the results of the pypsa optimization models."""
    def __init__(self, n: pypsa.Network, scenario_name: str = ""):
        self.network = n
        dispatch_series_dict = {}
        capacity_dict = {}

        # --- generators ---
        for gen in n.generators.index:
            dispatch_series_dict[gen] = n.generators_t.p[gen]
            capacity_dict[gen] = n.generators.loc[gen, "p_nom_opt"]

        # --- links: only those whose bus1 is an electricity bus ---
        for link in n.links.index:
            bus1 = n.links.loc[link, "bus1"]
            # electricity buses follow the pattern "bus_{country}" with no suffix
            bus1_name = bus1.replace("bus_", "")
            if "_" not in bus1_name:  # excludes bus_BE_heat, bus_BE_ch4 etc.
                if link in n.links_t.p1.columns:
                    # p1 is negative in PyPSA convention (power into bus1)
                    dispatch_series_dict[link] = -n.links_t.p1[link]
                    capacity_dict[link] = n.links.loc[link, "p_nom_opt"]

        self.dispatch_series_dict = dispatch_series_dict
        self.capacity_dict = capacity_dict
        self.scenario_name = scenario_name
        technologies_disp = ["biomass CHP", "CCGT", "coal", "gas boiler steam", "industrial heat pump high temperature", "nuclear", "OCGT"]
        technologies_vol = ["offwind", "onwind", "solar"]
        countries = ["FR", "BE", "NL", "DE_LU"]

        self.LABEL_MAP = {}

        for country in countries:
            for tech in technologies_disp:
                key = f"generator_disp_{country}_{tech}"
                value = f"{country} {tech}"
                self.LABEL_MAP[key] = value
            for tech in technologies_vol:
                key = f"generator_vol_{country}_{tech}"
                value = f"{country} {tech}"
                self.LABEL_MAP[key] = value

        self.TECH_COLORS = {
            "CCGT":           "#e96f23",
            "OCGT":           "#a86326",
            "Nuclear":        "#9467bd",
            "Biomass CHP":    "#2ca02c",
            "Solar":          "#dbc12b",
            "Onshore Wind":   "#74c0e0",
            "Offshore Wind":  "#1f77b4",
            "Pumped Hydro":   "#362e60",
            "Oil":            "#d62728",
            "Coal":           "#3D3D3D",
            "Heat Pump (HT)": "#ff0e6a",
            "Li-Ion (LFP)":   "#bcbd22",

        }

        self.DISPLAY_NAMES = {
            "CCGT":                                    "CCGT",
            "OCGT":                                    "OCGT",
            "nuclear":                                 "Nuclear",
            "coal":                                    "Coal",
            "biomass CHP":                             "Biomass CHP",
            "gas boiler steam":                        "Gas Boiler Steam",
            "industrial heat pump high temperature":   "Heat Pump (HT)",
            "offwind":                                 "Offshore Wind",
            "onwind":                                  "Onshore Wind",
            "solar":                                   "Solar",
            "Pumped-Storage-Hydro-bicharger":          "Pumped Hydro",
            "Lithium-Ion-LFP-bicharger":               "Li-Ion (LFP)",
        }

    def _make_path(self, default_name: str) -> str:
        if self.scenario_name:
            prefix = self.scenario_name + "_"
        else:
            prefix = ""
        os.makedirs("results", exist_ok=True)
        return f"results/{prefix}{default_name}.png"

    def _get_label(self, key: str) -> str:
        """Extract a human-readable label from a generator key, ignoring country."""
        parts = key.split("_")
        try:
            type_idx = next(i for i, p in enumerate(parts) if p in ("disp", "vol", "storage"))
            # everything after the type token is COUNTRY_tech, but country may
            # contain underscores (e.g. DE_LU), so match against known countries
            remainder = parts[type_idx + 1:]  # e.g. ["DE", "LU", "CCGT"]
            known_countries = [b.replace("bus_", "") for b in self.network.buses.index]
            # try progressively longer country prefixes until one matches
            country_token = ""
            tech_parts = remainder
            for i in range(1, len(remainder)):
                candidate = "_".join(remainder[:i])
                if candidate in known_countries:
                    country_token = candidate
                    tech_parts = remainder[i:]
            normalized = "_".join(parts[:type_idx + 1]) + "_" + "_".join(tech_parts)
        except StopIteration:
            normalized = key
            tech_parts = parts

        raw = self.LABEL_MAP.get(normalized, "_".join(tech_parts))
        return self.DISPLAY_NAMES.get(raw, raw)


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
            self.TECH_COLORS.get(self._get_label(key), cm.tab10(i / len(self.dispatch_series_dict)))
            for i, key in enumerate(self.dispatch_series_dict.keys())
        ]  # create colors dynamically
        end_summer = start_summer + pd.Timedelta(days=7)
        end_winter = start_winter + pd.Timedelta(days=7)

        active_keys = [k for k, s in self.dispatch_series_dict.items() if s.sum() > 0]

        summer_dict = {
            label: self.dispatch_series_dict[label].loc[start_summer:end_summer]
            for label in active_keys
        }
        winter_dict = {
            label: self.dispatch_series_dict[label].loc[start_winter:end_winter]
            for label in active_keys
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
                    label=self._get_label(label),
                    color=color,
                    linewidth=1.8,
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
                fontsize=16, framealpha=0.7, bbox_to_anchor=(0.5, -0.08))

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
                type_idx = next(i for i, p in enumerate(parts) if p in ("disp", "vol", "storage"))
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
        all_labels = [self._get_label(key) for key in all_keys]
        label_to_color = {
            label: self.TECH_COLORS.get(label, cm.tab10(i / len(all_labels)))
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
                label = self._get_label(key)
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

    def plot_installed_capacity(self, name="installed_capacity") -> None:
        """
        Plot and save a stacked horizontal bar chart of installed capacities (MW).
        One bar per country, with consistent technology colours and a shared legend.
        Works for both single-country (C) and multi-country (D) setups.
        """
        # --- gather capacity per country ---
        country_capacities = {}  # {country: {key: MW}}

        # generators
        for gen in self.network.generators.index:
            cap = self.network.generators.loc[gen, "p_nom_opt"]
            if cap <= 0:
                continue
            parts = gen.split("_")
            try:
                type_idx = next(i for i, p in enumerate(parts) if p in ("disp", "vol", "storage"))
                remainder = parts[type_idx + 1:]
                known_countries = [b.replace("bus_", "") for b in self.network.buses.index]
                country = ""
                for i in range(1, len(remainder)):
                    candidate = "_".join(remainder[:i])
                    if candidate in known_countries:
                        country = candidate
                        break
            except StopIteration:
                country = "unknown"

            if not country:
                country = "unknown"
            if country not in country_capacities:
                country_capacities[country] = {}
            country_capacities[country][gen] = cap

        # storage units
        for su in self.network.storage_units.index:
            cap = self.network.storage_units.loc[su, "p_nom_opt"]
            if cap <= 0:
                continue
            parts = su.split("_")
            try:
                type_idx = next(i for i, p in enumerate(parts) if p in ("disp", "vol", "storage"))
                remainder = parts[type_idx + 1:]
                known_countries = [b.replace("bus_", "") for b in self.network.buses.index]
                country = ""
                for i in range(1, len(remainder)):
                    candidate = "_".join(remainder[:i])
                    if candidate in known_countries:
                        country = candidate
                        break
            except StopIteration:
                country = "unknown"

            if not country:
                country = "unknown"
            if country not in country_capacities:
                country_capacities[country] = {}
            country_capacities[country][su] = cap

        # links: only those whose bus1 is an electricity bus
        for link in self.network.links.index:
            bus1 = self.network.links.loc[link, "bus1"]
            bus1_name = bus1.replace("bus_", "")
            if "_" not in bus1_name:  # excludes heat, ch4 buses
                cap = self.network.links.loc[link, "p_nom_opt"]
                if cap <= 0:
                    continue
                parts = link.split("_")
                try:
                    type_idx = next(i for i, p in enumerate(parts) if p in ("disp", "vol", "storage"))
                    remainder = parts[type_idx + 1:]
                    known_countries = [b.replace("bus_", "") for b in self.network.buses.index]
                    country = ""
                    for i in range(1, len(remainder)):
                        candidate = "_".join(remainder[:i])
                        if candidate in known_countries:
                            country = candidate
                            break
                except StopIteration:
                    country = "unknown"

                if not country:
                    country = "unknown"
                if country not in country_capacities:
                    country_capacities[country] = {}
                country_capacities[country][link] = cap

        countries = list(country_capacities.keys())

        # --- global colour map keyed by technology label ---
        all_keys = sorted({k for c in country_capacities.values() for k in c.keys()})
        all_labels = [self._get_label(k) for k in all_keys]
        seen = {}
        for key, label in zip(all_keys, all_labels):
            if label not in seen:
                seen[label] = key
        unique_labels = list(seen.keys())

        label_to_color = {
            label: self.TECH_COLORS.get(label, cm.tab10(i / len(unique_labels)))
            for i, label in enumerate(unique_labels)
        }

        # --- layout ---
        n_countries      = len(countries)
        BAR_HEIGHT       = 0.5
        BAR_SPACING      = 1.0
        INLINE_THRESHOLD = 8    # % of total bar width
        stagger_offsets  = [0.0, 0.18]

        fig_height = max(3, n_countries * 1.8 + 1.5)
        fig, ax = plt.subplots(figsize=(12, fig_height))

        legend_handles = {}
        all_outside    = []

        for c_idx, country in enumerate(countries):
            bar_y = c_idx * BAR_SPACING
            caps  = country_capacities[country]
            total = sum(caps.values())

            # sort descending
            caps = dict(sorted(caps.items(), key=lambda x: x[1], reverse=True))

            left = 0.0
            for key, cap in caps.items():
                label = self._get_label(key)
                color = label_to_color[label]
                pct   = cap / total * 100

                bar = ax.barh(
                    bar_y, pct, left=left,
                    height=BAR_HEIGHT,
                    color=color,
                    edgecolor="white",
                    linewidth=1.2,
                )

                if label not in legend_handles:
                    legend_handles[label] = bar[0]

                mid_x = left + pct / 2

                if pct >= INLINE_THRESHOLD:
                    ax.text(
                        mid_x, bar_y,
                        f"{label}\n{cap/1000:,.2f} GW",
                        va="center", ha="center",
                        fontsize=7.5, color="white", fontweight="bold",
                    )
                else:
                    all_outside.append((mid_x, label, cap, bar_y))

                left += pct

            # total label to the right
            ax.text(
                101, bar_y,
                f"Total: {total/1000:,.2f} GW",
                va="center", ha="left",
                fontsize=8.5, fontstyle="italic",
            )

        # --- outside labels with leader lines ---
        from itertools import groupby
        all_outside_sorted = sorted(all_outside, key=lambda x: x[3])
        for bar_y, group in groupby(all_outside_sorted, key=lambda x: x[3]):
            for idx, (mid_x, label, cap, _) in enumerate(group):
                y_offset = stagger_offsets[idx % len(stagger_offsets)]
                label_y  = bar_y + BAR_HEIGHT / 2 + 0.18 + y_offset
                ax.annotate(
                    f"{label}: {cap/1000:,.2f} GW",
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
            (n_countries - 1) * BAR_SPACING + BAR_HEIGHT + 0.8,
        )
        ax.set_yticks([c * BAR_SPACING for c in range(n_countries)])
        ax.set_yticklabels(countries, fontsize=11)
        ax.set_xlabel("Share of Total Installed Capacity (%)")
        ax.spines[["top", "right", "left"]].set_visible(False)

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
        labels = []
        data = []
        for key, vals in self.capacity_dict.items():
            if all(v == 0 for v in vals):
                continue
            labels.append(self._get_label(key))
            data.append(vals)

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
        Plot monthly average capacity factors per technology, with one line per
        year, all overlaid on a single Jan–Dec x-axis.
        """
        available_techs = input_data.cf[(country, input_data.config["years"][0])].columns
        technologies = [tech for tech in ["solar", "onwind", "offwind", "hydro"]
                        if tech in available_techs]
        label_tech_map = {
            "solar": "Solar",
            "onwind":        "Onshore Wind",
            "offwind":       "Offshore Wind",
            "hydro":         "Hydro",
        }

        years  = input_data.config["years"]
        colors = [cm.tab10(i / len(years)) for i in range(len(years))]
        months = np.arange(1, 13)
        month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        fig, axes = plt.subplots(1, len(technologies), figsize=(14, 4), sharey=True)
        if len(technologies) == 1:
            axes = [axes]

        for i, tech in enumerate(technologies):
                ax = axes[i]
                for year, color in zip(years, colors):
                    cf = input_data.cf[(country, year)][tech]
                    monthly_mean = cf.groupby(cf.index.month).mean()
                    ax.plot(
                        monthly_mean.index,
                        monthly_mean.values,
                        color=color,
                        linewidth=1.8,
                        label=str(year),
                    )

                ax.set_title(label_tech_map.get(tech, tech), fontsize=11)
                ax.set_ylim(0, 0.8)
                ax.set_xticks(months)
                ax.set_xticklabels(month_labels, fontsize=9, rotation=45)
                ax.grid(alpha=0.3, linestyle="--")
                ax.spines[["top", "right"]].set_visible(False)

        axes[0].set_ylabel("Capacity Factor", fontsize=11)
        axes[0].legend(title="Year", fontsize=9, framealpha=0.7, ncol=1, 
               loc="upper left", bbox_to_anchor=(0.08, 1.0))

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
            k for k in set(self.dispatch_series_dict.keys()) | set(other.dispatch_series_dict.keys())
            if (self.dispatch_series_dict.get(k, pd.Series(0)).sum() > 0 or
                other.dispatch_series_dict.get(k, pd.Series(0)).sum() > 0)
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
                    label=self._get_label(key),
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
                label = self._get_label(unit)

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
    
    def plot_scenario_comparison(
        self,
        other: "Visualizer",
        self_label: str = "C",
        other_label: str = "F",
        name: str = "scenario_comparison",
    ) -> None:
        """
        Grouped vertical bar chart comparing dispatch (TWh) per technology
        between two scenarios for Belgium.
        """
        # collect all technology labels across both scenarios
        all_keys = sorted(
            set(self.dispatch_series_dict.keys()) | set(other.dispatch_series_dict.keys())
        )
        all_labels = [self._get_label(k) for k in all_keys]

        # deduplicate while preserving order
        seen = {}
        for key, label in zip(all_keys, all_labels):
            if label not in seen:
                seen[label] = key
        unique_labels = list(seen.keys())
        unique_keys   = list(seen.values())

        def get_twh(vis, key):
            s = vis.dispatch_series_dict.get(key)
            return s.sum() / 1e6 if s is not None else 0.0

        values_self  = [get_twh(self, k)  for k in unique_keys]
        values_other = [get_twh(other, k) for k in unique_keys]

        filtered = [(l, k, vs, vo) for l, k, vs, vo in zip(unique_labels, unique_keys, values_self, values_other) if vs > 0 or vo > 0]
        unique_labels, unique_keys, values_self, values_other = map(list, zip(*filtered)) if filtered else ([], [], [], [])

        x      = np.arange(len(unique_labels))
        width  = 0.35
        colors = [self.TECH_COLORS.get(l, cm.tab10(i / len(unique_labels)))
                for i, l in enumerate(unique_labels)]

        fig, ax = plt.subplots(figsize=(10, 5))

        for i, (label, v_self, v_other, color) in enumerate(
            zip(unique_labels, values_self, values_other, colors)
        ):
            ax.bar(x[i] - width / 2, v_self,  width, color=color, alpha=1.0,
                edgecolor="white", linewidth=0.8)
            ax.bar(x[i] + width / 2, v_other, width, color=color, alpha=0.45,
                edgecolor="white", linewidth=0.8)

        # scenario legend entries
        from matplotlib.patches import Patch
        scenario_handles = [
            Patch(facecolor="grey", alpha=1.0,  label=self_label),
            Patch(facecolor="grey", alpha=0.45, label=other_label),
        ]
        # technology legend entries
        tech_handles = [
            Patch(facecolor=self.TECH_COLORS.get(l, cm.tab10(i / len(unique_labels))),
                label=l)
            for i, l in enumerate(unique_labels)
        ]

        ax.set_xticks(x)
        ax.set_xticklabels(unique_labels, fontsize=10)
        ax.set_ylabel("Dispatch (TWh)", fontsize=12)
        ax.set_ylim(bottom=0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

        # two-part legend: scenarios on top, technologies below
        leg1 = ax.legend(handles=scenario_handles, loc="upper right", fontsize=10,
                        framealpha=0.7, title="Scenario")
        ax.add_artist(leg1)
        ax.legend(handles=tech_handles, loc="upper left", fontsize=9,
                framealpha=0.7, title="Technology", ncol=2)

        fig.tight_layout()
        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()


    def plot_co2_sensitivity(
        self,
        networks_f: dict,
        ref_co2: float,
        name: str = "co2_sensitivity",
    ) -> None:
        """
        Stacked area chart showing dispatch (TWh) per technology as a function
        of the CO2 constraint expressed as % of the 1990 reference level.
        """
        all_keys = []
        for percent, nf in networks_f.items():
            n = nf.network
            for gen in n.generators.index:
                if n.generators_t.p[gen].sum() > 0 and gen not in all_keys:
                    all_keys.append(gen)
            for link in n.links.index:
                bus1 = n.links.loc[link, "bus1"]
                bus1_name = bus1.replace("bus_", "")
                if "_" not in bus1_name and link in n.links_t.p1.columns:
                    if (-n.links_t.p1[link]).sum() > 0 and link not in all_keys:
                        all_keys.append(link)
        all_keys = sorted(all_keys)

        all_labels = [self._get_label(k) for k in all_keys]
        seen = {}
        for key, label in zip(all_keys, all_labels):
            if label not in seen:
                seen[label] = key
        unique_labels = list(seen.keys())
        unique_keys   = list(seen.values())

        percents = sorted(networks_f.keys())
        x_vals   = [p * 100 for p in percents]

        dispatch = np.zeros((len(unique_keys), len(percents)))
        for j, percent in enumerate(percents):
            nf = networks_f[percent]
            n  = nf.network
            for i, key in enumerate(unique_keys):
                if key in n.generators_t.p.columns:
                    dispatch[i, j] = n.generators_t.p[key].sum() / 1e6
                elif key in n.links.index:
                    bus1 = n.links.loc[key, "bus1"]
                    bus1_name = bus1.replace("bus_", "")
                    if "_" not in bus1_name and key in n.links_t.p1.columns:
                        dispatch[i, j] = (-n.links_t.p1[key]).sum() / 1e6

        colors = [
            self.TECH_COLORS.get(l, cm.tab10(i / len(unique_labels)))
            for i, l in enumerate(unique_labels)
        ]

        fig, ax = plt.subplots(figsize=(10, 5))

        # stacked area: fill between cumulative sums
        bottom = np.zeros(len(percents))
        for i, (label, color) in enumerate(zip(unique_labels, colors)):
            top = bottom + dispatch[i]
            ax.fill_between(x_vals, bottom, top, color=color, alpha=0.85,
                            label=label, linewidth=0)
            bottom = top

        # reference line at 100%
        ax.axvline(100, color="black", linewidth=1, linestyle="--", alpha=0.5,
                label="1990 reference")

        ax.set_xlabel("CO₂ constraint (% of 1990 reference)", fontsize=12)
        ax.set_ylabel("Dispatch (TWh)", fontsize=12)
        ax.set_xlim(min(x_vals), max(x_vals))
        ax.set_ylim(bottom=0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.legend(loc="upper left", fontsize=9, framealpha=0.7,
                ncol=2, title="Technology")

        fig.tight_layout()
        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()

    def plot_line_utilisation_bar(
        self,
        name: str = "line_utilisation_bar",
    ) -> None:
        """
        Grouped bar chart showing average and peak utilisation (%) for each line.
        """
        lines      = self.network.lines
        flows      = self.network.lines_t.p0

        if lines.empty:
            print("No lines found in network — skipping plot.")
            return

        line_names = lines.index.tolist()
        avg_util   = (flows.abs().mean() / lines["s_nom"] * 100).reindex(line_names).fillna(0)
        peak_util  = (flows.abs().max()  / lines["s_nom"] * 100).reindex(line_names).fillna(0)

        x     = np.arange(len(line_names))
        width = 0.35

        fig, ax = plt.subplots(figsize=(10, 5))

        ax.bar(x - width / 2, avg_util.values,  width, label="Average utilisation",
            color="#1f77b4", alpha=0.85, edgecolor="white", linewidth=0.8)
        ax.bar(x + width / 2, peak_util.values, width, label="Peak utilisation",
            color="#e07b3b", alpha=0.85, edgecolor="white", linewidth=0.8)

        # value labels on top of each bar
        for xi, (avg, peak) in enumerate(zip(avg_util.values, peak_util.values)):
            ax.text(xi - width / 2, avg  + 0.5, f"{avg:.1f}%",  ha="center", va="bottom", fontsize=8)
            ax.text(xi + width / 2, peak + 0.5, f"{peak:.1f}%", ha="center", va="bottom", fontsize=8)

        ax.set_xticks(x)
        ax.set_xticklabels(line_names, fontsize=10)
        ax.set_ylabel("Utilisation (%)", fontsize=12)
        ax.set_ylim(0, max(peak_util.max() * 1.15, 10))
        ax.axhline(100, color="red", linewidth=0.8, linestyle="--", alpha=0.5, label="100% capacity")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.legend(fontsize=10, framealpha=0.7)

        fig.tight_layout()
        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()


    def plot_network_diagram(
        self,
        name: str = "network_diagram",
    ) -> None:
        """
        Schematic network diagram with countries as nodes and lines as edges,
        coloured by average utilisation (green → red).
        """
        import matplotlib.cm as mcm
        import matplotlib.colors as mcolors
        from matplotlib.patches import FancyArrowPatch

        network_lines = self.network.lines
        flows         = self.network.lines_t.p0

        if network_lines.empty:
            print("No lines found in network — skipping plot.")
            return

        # approximate geographic positions {country: (lon, lat)} in plot units
        COUNTRY_POS = {
            "BE":    (4.5,  50.8),
            "FR":    (2.5,  46.5),
            "NL":    (5.3,  52.3),
            "DE_LU": (10.0, 51.2),
        }

        # fall back to circle layout for any country not in the map
        buses = [b.replace("bus_", "") for b in self.network.buses.index
                if "heat" not in b and "ch4" not in b]
        for i, bus in enumerate(buses):
            if bus not in COUNTRY_POS:
                angle = 2 * np.pi * i / len(buses)
                COUNTRY_POS[bus] = (5 + 3 * np.cos(angle), 50 + 3 * np.sin(angle))

        # utilisation per line
        #avg_util = (flows.abs().mean() / lines["s_nom"] * 100).fillna(0) # %
        avg_flow = flows.abs().mean().fillna(0)          # MW
        avg_util = (avg_flow / network_lines["s_nom"] * 100).fillna(0)   # % for colour

        cmap  = mcm.RdYlGn_r          # green=low, red=high
        norm  = mcolors.Normalize(vmin=80, vmax=100)
        sm    = mcm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])

        fig, ax = plt.subplots(figsize=(8, 7))

        # --- draw lines ---
        for line_name, row in network_lines.iterrows():
            bus0 = row["bus0"].replace("bus_", "")
            bus1 = row["bus1"].replace("bus_", "")

            if bus0 not in COUNTRY_POS or bus1 not in COUNTRY_POS:
                continue

            x0, y0 = COUNTRY_POS[bus0]
            x1, y1 = COUNTRY_POS[bus1]
            util    = avg_util.get(line_name, 0)
            color   = cmap(norm(util))

            ax.plot([x0, x1], [y0, y1], color=color, linewidth=3, solid_capstyle="round", zorder=1)

            # utilisation label at midpoint
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            ax.text(mx, my, f"{avg_flow.get(line_name, 0):,.0f} MW", ha="center", va="center",
                fontsize=8, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8),
                zorder=3)

        # --- draw nodes ---
        for bus in buses:
            if bus not in COUNTRY_POS:
                continue
            x, y = COUNTRY_POS[bus]
            ax.scatter(x, y, s=600, color="#2c3e50", zorder=4)
            ax.text(x, y, bus, ha="center", va="center",
                    fontsize=9, fontweight="bold", color="white", zorder=5)

        # --- colorbar ---
        cbar = fig.colorbar(sm, ax=ax, orientation="vertical", fraction=0.03, pad=0.02)
        cbar.set_label("Average utilisation (%)", fontsize=10)

        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title("Transmission line utilisation", fontsize=13, pad=12)

        fig.tight_layout()
        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()

    def plot_load_duration_curve(
        self,
        name: str = "load_duration_curve",
    ) -> None:
        """
        Plot a load duration curve for total generation and each technology.
        Each series is independently sorted descending. X-axis shows hours,
        Y-axis shows power in MW.
        """
        fig, ax = plt.subplots(figsize=(12, 5))

        # --- total generation ---
        total = sum(s for s in self.dispatch_series_dict.values())
        total_sorted = np.sort(total.values)[::-1]/1000  # MW → GW
        hours = np.arange(1, len(total_sorted) + 1)

        ax.plot(
            hours, total_sorted,
            color="black", linewidth=2.5, label="Total", zorder=5
        )

        # --- per technology ---
        for key, series in self.dispatch_series_dict.items():
            if series.sum() <= 0:
                continue
            label = self._get_label(key)
            color = self.TECH_COLORS.get(label, cm.tab10(
                list(self.dispatch_series_dict.keys()).index(key) /
                len(self.dispatch_series_dict)
            ))
            sorted_series = np.sort(series.values)[::-1]/1000  # MW → GW

            ax.plot(
                np.arange(1, len(sorted_series) + 1),
                sorted_series,
                color=color, linewidth=1.2, alpha=0.85, label=label,
            )

        ax.set_xlabel("Hours (sorted)", fontsize=12)
        ax.set_ylabel("Power (GW)", fontsize=12)
        ax.set_xlim(0, len(total_sorted))
        ax.set_ylim(bottom=0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.grid(axis="x", linestyle=":", alpha=0.3)
        ax.legend(fontsize=9, framealpha=0.7, ncol=2)

        fig.tight_layout()
        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()

    def get_energy_transport_table(self):
        """
        Compute total transported energy by electricity lines and CH4 pipelines.
        Returns a pandas DataFrame with values in TWh.
        """
        # Electricity transport through AC lines
        electricity_transport = self.network.lines_t.p0.abs().sum().sum()

        # Gas transport through CH4 pipeline links only
        ch4_links = [link for link in self.network.links.index if link.startswith("CH4_")]

        if ch4_links:
            gas_transport = self.network.links_t.p0[ch4_links].abs().sum().sum()
        else:
            gas_transport = 0.0

        data = {
            "Network": ["Electricity", "CH4 gas"],
            "Transported energy [TWh]": [
                electricity_transport / 1e6,
                gas_transport / 1e6,
            ],
        }

        return pd.DataFrame(data)

    def plot_energy_transport_comparison(self, name="energy_transport_comparison"):
        """
        Plot a bar chart comparing total transported energy in the electricity
        network and the CH4 gas network.
        """
        transport_df = self.get_energy_transport_table()

        fig, ax = plt.subplots(figsize=(6, 4))

        ax.bar(
            transport_df["Network"],
            transport_df["Transported energy [TWh]"],
            edgecolor="white",
            linewidth=1.0,
        )

        ax.set_ylabel("Transported energy [TWh]")
        ax.set_title("Energy transport comparison")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

        for i, value in enumerate(transport_df["Transported energy [TWh]"]):
            ax.text(
                i,
                value,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

        fig.tight_layout()
        plt.savefig(self._make_path(name), dpi=150, bbox_inches="tight")
        plt.close()

        return transport_df