
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 01_Overview.py
# PURPOSE: Master heatmap showing seasonal return patterns across all
#          investable asset classes. Bird's eye view of seasonal tendencies.
#
# MULTI-ASSET RULES:
#   - filter_for_multiasset removes yield/spread/rate/index series and
#     Macro/Volatility classes. All values are price returns in % terms.
#   - Fixed Income in Domestic scope has no investable price-return series
#     (Bond ETFs are international_etf, only visible in Global scope).
#     A note is shown prompting the user to switch to Global scope.
#   - Every st.plotly_chart call has a unique key= to prevent duplicate ID errors.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st


from utils.data_loader import (
    load_metadata, load_seasonality_stats, load_monthly_returns,
    filter_by_market_scope, render_sidebar, inject_css,
    build_heatmap, prepare_stats, filter_for_multiasset,
    THEME, MONTHS, MONTH_FULL
)
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="Overview · Scripbox Seasonality",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
render_sidebar()

# ── READ CONTROLS ─────────────────────────────────────────────────────────────
scope          = st.session_state.get("market_scope", "Domestic")
currency       = st.session_state.get("currency", "local")
sig_filter     = st.session_state.get("sig_filter", "All patterns")
lookback       = st.session_state.get("lookback_years", 25)
heatmap_metric = st.session_state.get("heatmap_metric", "Average Return")

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
stats_all, meta = prepare_stats(currency, scope, lookback)

if sig_filter == "p < 0.10":
    stats_all = stats_all[stats_all["p_value"] < 0.10]
elif sig_filter == "p < 0.05":
    stats_all = stats_all[stats_all["p_value"] < 0.05]

metric_col = "avg_return" if heatmap_metric == "Average Return" else "median_return"

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Seasonality Overview</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Seasonal return patterns across all asset classes · {scope} scope ·
    {"INR" if currency == "inr" else "Local Currency"} · {heatmap_metric}
    </div>''',
    unsafe_allow_html=True
)

# ── SUMMARY METRIC CARDS ──────────────────────────────────────────────────────
total_series  = meta["name"].nunique()
sig_series    = stats_all[stats_all["p_value"] < 0.05]["name"].nunique()
years_of_data = datetime.today().year - 2000
asset_classes = meta["asset_class"].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Asset Series", total_series)
col2.metric("Statistically Significant Patterns", sig_series)
col3.metric("Years of History", f"{years_of_data}Y")
col4.metric("Asset Classes", asset_classes)

st.markdown("<hr>", unsafe_allow_html=True)

# ── TWO VIEWS ─────────────────────────────────────────────────────────────────
view_tabs = st.tabs([
    "Investable Assets",
    "Full Reference (incl. Macro & Volatility)"
])

# ── VIEW 1: INVESTABLE ASSETS ─────────────────────────────────────────────────
with view_tabs[0]:

    stats_investable = filter_for_multiasset(stats_all)

    AC_ORDER = ["Equity", "Fixed Income", "Commodity", "FX", "Mutual Fund"]
    available_acs = [
        ac for ac in AC_ORDER
        if ac in stats_investable["asset_class"].values
    ]

    if not available_acs:
        st.info("No investable price-return series available under current filters.")
    else:
        ac_tabs = st.tabs(available_acs)

        for tab_idx, (ac_tab, asset_class) in enumerate(zip(ac_tabs, available_acs)):
            with ac_tab:
                ac_stats = stats_investable[
                    stats_investable["asset_class"] == asset_class
                ].copy()

                if ac_stats.empty:
                    if asset_class == "Fixed Income" and scope == "Domestic":
                        st.markdown(
                            f'''<div class="info-card">
                            In <strong>Domestic scope</strong>, Fixed Income has no
                            investable price-return series. Bond ETFs (TLT, HYG,
                            India Bond ETF) are accessible via LRS and appear in
                            <strong>Global scope</strong>. Switch to Global in the
                            sidebar to see Fixed Income in this view. Yield and
                            spread series (India 10Y, US Treasuries) are shown on
                            the dedicated Fixed Income page with basis point units.
                            </div>''',
                            unsafe_allow_html=True
                        )
                    else:
                        st.info(
                            f"No price-return series for {asset_class} "
                            f"under current filters."
                        )
                    continue

                pivot = ac_stats.pivot_table(
                    index="name", columns="month",
                    values=metric_col, aggfunc="mean"
                )
                pivot = pivot.reindex(columns=range(1, 13))
                pivot.columns = MONTHS

                inv_map = dict(zip(meta["name"], meta["investability"]))
                pivot.index = [
                    f"{n} [Ref]" if inv_map.get(n) == "benchmark" else n
                    for n in pivot.index
                ]

                fig = build_heatmap(
                    pivot_df=pivot,
                    value_col_label="Return (%)",
                    is_basis_points=False,
                )
                # Unique key: view + asset class index + tab index
                st.plotly_chart(
                    fig, use_container_width=True,
                    key=f"overview_inv_{tab_idx}_{asset_class.replace(' ','_')}"
                )
                st.caption(
                    f"{len(pivot)} series · {asset_class} · "
                    f"[Ref] = reference benchmark · {heatmap_metric}"
                )

    st.markdown(
        f'''<div class="info-card" style="margin-top:1rem;">
        <strong>What is excluded from this view?</strong>
        Yield and spread series are on the Fixed Income page in basis points.
        Macro indicators and Volatility indices are reference data not
        investable assets — visible in the Full Reference tab above.
        In Domestic scope, Bond ETFs are not shown here because they require
        LRS access — switch to Global scope to include them.
        </div>''',
        unsafe_allow_html=True
    )

# ── VIEW 2: FULL REFERENCE ────────────────────────────────────────────────────
with view_tabs[1]:

    st.markdown(
        f'''<div class="synthetic-note">
        This view includes Macro and Volatility series alongside investable
        assets. Macro series (GDP, CPI, unemployment) are economic readings
        — their monthly changes are not investment returns. Use for reference only.
        </div>''',
        unsafe_allow_html=True
    )

    AC_ORDER_FULL = [
        "Equity", "Fixed Income", "Commodity", "FX",
        "Mutual Fund", "Volatility", "Macro"
    ]
    available_full = [
        ac for ac in AC_ORDER_FULL
        if ac in stats_all["asset_class"].values
    ]

    full_tabs = st.tabs(available_full)

    for tab_idx, (full_tab, asset_class) in enumerate(zip(full_tabs, available_full)):
        with full_tab:
            ac_stats = stats_all[stats_all["asset_class"] == asset_class].copy()

            if ac_stats.empty:
                st.info(f"No data for {asset_class} under current filters.")
                continue

            # For Fixed Income in full reference view: show Bond ETFs only
            # Yield and spread series are on the dedicated Fixed Income page
            if asset_class == "Fixed Income":
                ac_stats = ac_stats[
                    ~ac_stats["series_type"].isin({"yield", "spread", "rate"})
                ].copy()
                if ac_stats.empty:
                    st.info(
                        "Fixed Income yield and spread series are shown on "
                        "the Fixed Income page with basis point units."
                    )
                    continue

            pivot = ac_stats.pivot_table(
                index="name", columns="month",
                values=metric_col, aggfunc="mean"
            )
            pivot = pivot.reindex(columns=range(1, 13))
            pivot.columns = MONTHS

            inv_map = dict(zip(meta["name"], meta["investability"]))
            pivot.index = [
                f"{n} [Ref]" if inv_map.get(n) == "benchmark" else n
                for n in pivot.index
            ]

            fig = build_heatmap(
                pivot_df=pivot,
                value_col_label="Return (%)",
                is_basis_points=False,
            )
            # Unique key: full reference view + asset class index + tab index
            st.plotly_chart(
                fig, use_container_width=True,
                key=f"overview_full_{tab_idx}_{asset_class.replace(' ','_')}"
            )
            st.caption(
                f"{len(pivot)} series · {asset_class} · "
                f"[Ref] = reference benchmark · {heatmap_metric}"
            )

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown(f"""
**What is seasonality?**

Seasonality refers to the tendency of an asset's price to move in a
predictable direction during certain months of the year. These patterns
repeat across years and can be used as one input in investment decisions.

**What does each colour mean?**

Each cell shows the {heatmap_metric.lower()} return for that asset in
that month across all available years (up to 25 years of data).
Green = historically positive in that month.
Red = historically negative. Darker = stronger tendency.

**Why is Fixed Income missing from Domestic scope?**

Bond ETFs (TLT, HYG, India Bond ETF) are the Fixed Income instruments
with percentage price returns comparable to equities. These require LRS
access and are only visible in Global scope. In Domestic scope, the only
Fixed Income series is the India 10Y Government Bond yield — which is a
benchmark yield series shown in basis points on the dedicated Fixed Income
page, not a price return comparable to equities.

**Why are Macro and Volatility excluded from Investable Assets?**

GDP growth, CPI, and unemployment are economic readings, not investment
returns. VIX is a fear gauge. Mixing their monthly changes into an
investment return heatmap produces misleading comparisons. They appear
in the Full Reference tab and on their own dedicated pages.

**Average Return vs Median Return**

Average is influenced by extreme years. Median is the middle value and
is more robust to outliers. Toggle between them using the sidebar.

**Domestic vs Global scope**

Domestic: Indian markets and global benchmark indices.
Global: adds internationally accessible ETFs and assets via LRS.
""")
