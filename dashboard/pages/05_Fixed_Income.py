
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 05_Fixed_Income.py
# PURPOSE: Seasonal patterns across fixed income markets.
#
# UNIT HANDLING — CRITICAL:
#   Bond ETF series (series_type = price):
#     Stored as decimal returns (0.02 = 2%). Display multiplier = 100. Shows %.
#
#   Yield and spread series (series_type = yield or spread):
#     Stored in stats CSV as diff()*100 — already in basis points.
#     Example: avg_return = 2.37 means yield changed by +2.37 bps on average.
#     Display multiplier = 1. Shows bps as-is.
#     Use already_in_bps=True in build_heatmap for these series.
#
# This is the ONLY page where yield and spread series appear.
# On all other pages, filter_for_multiasset() removes them.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st


from utils.data_loader import (
    load_metadata, load_seasonality_stats,
    filter_by_market_scope, render_sidebar, inject_css,
    build_heatmap, prepare_stats, THEME, MONTHS, MONTH_FULL
)
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="Fixed Income · Scripbox Seasonality",
    page_icon="🏦",
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
stats = stats_all[stats_all["asset_class"] == "Fixed Income"].copy()
meta  = meta[meta["asset_class"] == "Fixed Income"].copy()

if sig_filter == "p < 0.10":
    stats = stats[stats["p_value"] < 0.10]
elif sig_filter == "p < 0.05":
    stats = stats[stats["p_value"] < 0.05]

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Fixed Income</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Seasonal patterns in bond yields, credit spreads, and fixed income ETFs ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"} ·
    {metric_label}
    </div>''',
    unsafe_allow_html=True
)

st.markdown(
    '''<div class="info-card">
    <strong>How to read this page:</strong> Bond ETF tabs show percentage
    price returns (%). Yield and spread tabs show monthly changes in basis
    points (bps), where 1 bps = 0.01%. For example, +20 bps means the
    yield rose by 0.20 percentage points that month on average.
    The two types are in separate tabs so the colour scale is meaningful.
    </div>''',
    unsafe_allow_html=True
)

# ── SUMMARY METRICS ───────────────────────────────────────────────────────────
total_fi    = meta["name"].nunique()
sig_fi      = stats[stats["p_value"] < 0.05]["name"].nunique()
etf_count   = meta[meta["investability"] == "international_etf"]["name"].nunique()
bmark_count = meta[meta["investability"] == "benchmark"]["name"].nunique()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Fixed Income Series", total_fi)
c2.metric("Significant Patterns (p<0.05)", sig_fi)
c3.metric("Investable Bond ETFs", etf_count)
c4.metric("Reference Benchmarks", bmark_count)

st.markdown("<hr>", unsafe_allow_html=True)

# ── PAGE-LEVEL FILTERS ────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Filter & Explore</div>''',
            unsafe_allow_html=True)

col_type, col_series = st.columns([1, 2])

with col_type:
    sub_options  = ["All"] + sorted(meta["sub_class"].dropna().unique().tolist())
    selected_sub = st.selectbox("Series Type", sub_options, key="fi_sub")

filtered_meta = meta.copy()
if selected_sub != "All":
    filtered_meta = filtered_meta[filtered_meta["sub_class"] == selected_sub]

filtered_names = set(filtered_meta["name"].tolist())
filtered_stats = stats[stats["name"].isin(filtered_names)].copy()

with col_series:
    series_list  = sorted(filtered_stats["name"].unique().tolist())
    default_name = "India 10Y Government Bond"
    default_idx  = series_list.index(default_name) if default_name in series_list else 0
    selected_series = st.selectbox(
        "Select series for detail view",
        series_list, index=default_idx, key="fi_series"
    )

if filtered_stats.empty:
    st.warning("No series match the current filter combination.")
    st.stop()

# ── DETERMINE UNITS FOR SELECTED SERIES ──────────────────────────────────────
# Yield and spread series in stats CSV are stored as diff()*100 = already bps
# Bond ETF price series are stored as decimal returns (0.02 = 2%)
series_meta  = filtered_meta[filtered_meta["name"] == selected_series]
series_type  = series_meta["series_type"].values[0] if len(series_meta) > 0 else "price"
is_yield     = series_type in ["yield", "spread"]
unit_label   = "bps" if is_yield else "%"
# For yield: values already in bps, multiply by 1
# For price: values in decimal, multiply by 100
multiplier   = 1 if is_yield else 100

# ── DETAIL CHART ──────────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Monthly Detail — Selected Series</div>''',
            unsafe_allow_html=True)

inv_type = filtered_meta[filtered_meta["name"] == selected_series]["investability"].values
if len(inv_type) > 0 and inv_type[0] == "benchmark":
    st.markdown(
        f'''<div class="info-card">
        <strong>{selected_series}</strong> is a reference benchmark —
        not directly investable but important for understanding interest
        rate conditions.
        </div>''',
        unsafe_allow_html=True
    )

if is_yield:
    st.markdown(
        f'''<div class="info-card">
        Values in <strong>basis points (bps)</strong>. 1 bps = 0.01%.
        +20 bps = yield rose by 0.20 percentage points.
        Positive = yields rose (bond prices fell).
        Negative = yields fell (bond prices rose).
        </div>''',
        unsafe_allow_html=True
    )

series_data = filtered_stats[filtered_stats["name"] == selected_series].copy()
series_data = series_data.sort_values("month")

fig_bar = go.Figure()

fig_bar.add_trace(go.Bar(
    x=MONTHS,
    y=series_data["avg_return"] * multiplier,
    name=f"Average ({unit_label})",
    marker_color=[
        THEME["positive"] if v >= 0 else THEME["negative"]
        for v in series_data["avg_return"]
    ],
    opacity=0.85,
    text=[f"{v*multiplier:+.1f} {unit_label}" for v in series_data["avg_return"]],
    textposition="outside",
    textfont=dict(size=9),
))

fig_bar.add_trace(go.Scatter(
    x=MONTHS,
    y=series_data["median_return"] * multiplier,
    name=f"Median ({unit_label})",
    mode="lines+markers",
    line=dict(color=THEME["primary"], width=2, dash="dot"),
    marker=dict(size=6, color=THEME["primary"]),
))

fig_bar.update_layout(
    paper_bgcolor=THEME["bg"], plot_bgcolor=THEME["bg"],
    font=dict(family=THEME["font"], color=THEME["text_primary"]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1, font=dict(size=11)),
    xaxis=dict(showgrid=False, tickfont=dict(size=11)),
    yaxis=dict(
        showgrid=True, gridcolor=THEME["border"],
        ticksuffix=f" {unit_label}", zeroline=True,
        zerolinecolor=THEME["border"], zerolinewidth=1.5,
        title=dict(
            text=f"Monthly Change ({unit_label})",
            font=dict(size=10)
        ),
    ),
    margin=dict(l=20, r=20, t=40, b=60),
    height=380,
)

st.plotly_chart(fig_bar, use_container_width=True, key="fi_detail_bar")

# ── SUPPORTING STATISTICS TABLE ───────────────────────────────────────────────
with st.expander("Show supporting statistics for selected series"):
    display_cols = ["month_name", "avg_return", "median_return",
                    "win_rate", "best_return", "best_year",
                    "worst_return", "worst_year", "n_obs", "p_value"]
    display_df = series_data[display_cols].copy()
    display_df.columns = ["Month", "Avg", "Median",
                          "Win Rate", "Best", "Best Year",
                          "Worst", "Worst Year", "Obs", "p-value"]
    for col in ["Avg", "Median", "Best", "Worst"]:
        display_df[col] = display_df[col].map(
            lambda x: f"{x*multiplier:+.1f} {unit_label}"
        )
    display_df["Win Rate"]   = display_df["Win Rate"].map(lambda x: f"{x*100:.0f}%")
    display_df["p-value"]    = display_df["p-value"].map(lambda x: f"{x:.3f}")
    display_df["Best Year"]  = display_df["Best Year"].map(
        lambda x: str(int(x)) if pd.notna(x) else ""
    )
    display_df["Worst Year"] = display_df["Worst Year"].map(
        lambda x: str(int(x)) if pd.notna(x) else ""
    )
    display_df["Obs"] = display_df["Obs"].map(
        lambda x: str(int(x)) if pd.notna(x) else ""
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── HEATMAP SECTION ───────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Heatmap — All Fixed Income Series</div>''',
            unsafe_allow_html=True)

st.markdown(
    '''<div class="info-card">
    Bond ETF tabs: values in %. Yield and spread tabs: values in bps.
    Kept separate so the colour scale is meaningful within each group.
    </div>''',
    unsafe_allow_html=True
)

SUB_CLASS_ORDER = [
    "Bond ETF",
    "Sovereign Yield", "US Treasury Yield",
    "Yield Curve Spread", "Credit Spread",
    "Inflation Expectation", "Real Yield", "Policy Rate"
]

available_subs = [s for s in SUB_CLASS_ORDER
                  if s in filtered_stats["sub_class"].values]

if selected_sub != "All":
    available_subs = [selected_sub] if selected_sub in available_subs else available_subs

if not available_subs:
    st.info("No sub-classes available for current filter combination.")
else:
    heatmap_tabs = st.tabs(available_subs)

    for tab_idx, (htab, sub) in enumerate(zip(heatmap_tabs, available_subs)):
        with htab:
            sub_stats = filtered_stats[filtered_stats["sub_class"] == sub].copy()

            if sub_stats.empty or sub_stats["avg_return"].isna().all():
    if sub in ["Credit Spread", "Yield Curve Spread"]:
        st.info(
            f"Insufficient history for {sub} seasonal analysis. "
            f"FRED data for these series is available from April 2023 only — "
            f"meaningful seasonality requires a minimum of 10 years of monthly observations. "
            f"This section will populate automatically once sufficient history accumulates."
        )
    else:
        st.info(f"No data for {sub} under current filters.")
    continue

            sub_types    = sub_stats["series_type"].unique()
            tab_is_yield = any(t in ["yield", "spread"] for t in sub_types)

            pivot = sub_stats.pivot_table(
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

            if tab_is_yield:
                # Values already in bps — use already_in_bps=True
                # multiplier = 1, unit = bps
                fig = build_heatmap(
                    pivot,
                    value_col_label="bps",
                    already_in_bps=True,
                )
                unit_note = "basis points (bps) — values already in bps"
            else:
                # Bond ETF price returns — decimal values, multiply by 100
                fig = build_heatmap(
                    pivot,
                    value_col_label="Return (%)",
                    is_basis_points=False,
                )
                unit_note = "percent (%)"

            st.plotly_chart(
                fig, use_container_width=True,
                key=f"fi_heatmap_{sub.replace(' ', '_')}_{tab_idx}"
            )
            st.caption(
                f"{len(pivot)} series · {sub} · Values in {unit_note} · "
                f"[Ref] = reference benchmark · {metric_label}"
            )

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown("""
**What is fixed income?**

Fixed income refers to investments that pay a defined return — primarily
bonds. When you buy a bond, you lend money to a government or company
in exchange for regular interest payments and return of principal at maturity.

**Bond ETFs (shown in %)**

Bond ETFs are exchange-traded funds holding a portfolio of bonds.
Returns are percentage price changes — exactly like equity ETFs.
A return of +2% means the ETF price rose 2% that month.
These are directly investable through LRS or Indian AMC international funds.

**Bond yields and spreads (shown in bps)**

Yields like the US 10Y Treasury Yield are interest rate levels.
Their monthly changes are tiny — typically 5-50 basis points (0.05%-0.50%).
We show them in basis points (bps) where 1 bps = 0.01%.

Positive bps = yield rose = bond prices fell.
Negative bps = yield fell = bond prices rose.
Yields and bond prices always move in opposite directions.

**Why separate tabs for ETFs and yields?**

A yield change of +20 bps and a bond ETF return of +2% look similar
as numbers but are completely different things. Showing them on the
same colour scale would be misleading. Separate tabs keep each group
internally comparable.

**Why do US Treasury yields matter for Indian investors?**

US yields set the global cost of money. When US yields rise, capital
tends to flow out of emerging markets like India, pressuring Indian
bonds, the rupee, and sometimes equities. Tracking yield seasonality
helps anticipate these capital flow cycles.

**India 10Y Government Bond**

This is the benchmark Indian government bond yield. Rising yields
signal tighter RBI monetary conditions, which is negative for bond
fund NAVs and can pressure equity valuations. The most important
domestic fixed income indicator for Indian investors.

**Credit spreads**

Spreads measure extra yield required to hold corporate bonds over
government bonds. Rising spreads mean investors are becoming risk-averse.
IG (investment grade) = stable large companies.
HY (high yield) = riskier companies, more volatile spreads.
""")
