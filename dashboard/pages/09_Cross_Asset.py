
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 09_Cross_Asset.py
# PURPOSE: Cross-asset seasonal analysis showing how different investable
#          asset classes behave in the same months simultaneously.
#
# FILTERING RULES:
#   - Macro and Volatility excluded from all views — not investable assets
#   - Yield and spread series excluded from multi-asset heatmaps and rankings
#     (different units — handled on dedicated Fixed Income page)
#   - Only price-return series shown so all values are in comparable % terms
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st


from utils.data_loader import (
    load_metadata, load_seasonality_stats,
    filter_by_market_scope, render_sidebar, inject_css,
    build_heatmap, prepare_stats, filter_for_multiasset,
    THEME, MONTHS, MONTH_FULL
)
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cross Asset · Scripbox Seasonality",
    page_icon="🔀",
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

# Apply multi-asset filter — removes yield/spread/rate/index series
# and removes Macro and Volatility asset classes
# All remaining series are price-return series in comparable % terms
stats = filter_for_multiasset(stats_all)

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Cross-Asset Seasonality</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    How investable asset classes behave in the same months ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"} ·
    {metric_label}
    </div>''',
    unsafe_allow_html=True
)

st.markdown(
    f'''<div class="info-card">
    All series shown are price-return series in percentage terms.
    Yield and spread series are excluded (shown on the Fixed Income page).
    Macro indicators and Volatility indices are excluded (not investable assets).
    This ensures all values on this page are directly comparable.
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 1: ASSET CLASS SUMMARY HEATMAP ───────────────────────────────────
# One row per investable asset class — average return across ALL price-type
# series in that class for each month. Highest-level cross-asset view.
st.markdown('''<div class="section-header">Asset Class Monthly Summary</div>''',
            unsafe_allow_html=True)

st.markdown(
    f'''<div class="info-card">
    Each row = average {metric_label.lower()} across all price-return series
    in that asset class for each month. Fixed Income row shows Bond ETF
    returns only — yield series are excluded to keep units comparable.
    </div>''',
    unsafe_allow_html=True
)

# Investable asset classes only — Macro and Volatility excluded
AC_ORDER = ["Equity", "Fixed Income", "Commodity", "FX", "Mutual Fund"]

ac_summary = (
    stats.groupby(["asset_class", "month"])[metric_col]
    .mean()
    .reset_index()
)
ac_pivot = ac_summary.pivot(index="asset_class", columns="month", values=metric_col)
ac_pivot = ac_pivot.reindex(columns=range(1, 13))
ac_pivot.columns = MONTHS
ac_pivot = ac_pivot.reindex([ac for ac in AC_ORDER if ac in ac_pivot.index])

fig_summary = build_heatmap(
    ac_pivot,
    value_col_label="Return (%)",
    height=max(300, len(ac_pivot) * 52 + 80)
)
st.plotly_chart(fig_summary, use_container_width=True)
st.caption(
    f"{len(ac_pivot)} investable asset classes · "
    f"Each cell = average {metric_label.lower()} across all price-return "
    f"series in that class"
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 2: MONTH DEEP-DIVE ────────────────────────────────────────────────
# Select a month and see how all investable asset classes and series ranked
st.markdown('''<div class="section-header">Month Deep-Dive</div>''',
            unsafe_allow_html=True)

selected_month_name = st.selectbox(
    "Select a month to analyse",
    options=list(MONTH_FULL.values()),
    index=0,
    key="cross_month"
)

month_num   = [k for k, v in MONTH_FULL.items() if v == selected_month_name][0]
month_stats = stats[stats["month"] == month_num].copy()

if not month_stats.empty:
    month_stats_sorted = month_stats.sort_values(metric_col, ascending=False)

    col_pos, col_neg = st.columns(2)

    with col_pos:
        st.markdown(
            f'''<p style="font-weight:600;color:{THEME["positive"]};
            font-size:0.9rem;">
            Top Seasonal Winners in {selected_month_name}</p>''',
            unsafe_allow_html=True
        )
        top_pos = month_stats_sorted.head(10)[
            ["name", "asset_class", metric_col, "win_rate", "p_value"]
        ].copy()
        top_pos.columns = ["Series", "Asset Class", metric_label, "Win Rate", "p-value"]
        top_pos[metric_label] = top_pos[metric_label].map(lambda x: f"{x*100:+.2f}%")
        top_pos["Win Rate"]   = top_pos["Win Rate"].map(lambda x: f"{x*100:.0f}%")
        top_pos["p-value"]    = top_pos["p-value"].map(lambda x: f"{x:.3f}")
        st.dataframe(top_pos, use_container_width=True, hide_index=True)

    with col_neg:
        st.markdown(
            f'''<p style="font-weight:600;color:{THEME["negative"]};
            font-size:0.9rem;">
            Top Seasonal Laggards in {selected_month_name}</p>''',
            unsafe_allow_html=True
        )
        top_neg = month_stats_sorted.tail(10).sort_values(metric_col)[
            ["name", "asset_class", metric_col, "win_rate", "p_value"]
        ].copy()
        top_neg.columns = ["Series", "Asset Class", metric_label, "Win Rate", "p-value"]
        top_neg[metric_label] = top_neg[metric_label].map(lambda x: f"{x*100:+.2f}%")
        top_neg["Win Rate"]   = top_neg["Win Rate"].map(lambda x: f"{x*100:.0f}%")
        top_neg["p-value"]    = top_neg["p-value"].map(lambda x: f"{x:.3f}")
        st.dataframe(top_neg, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Asset class average bar chart for selected month
    ac_month = (
        month_stats.groupby("asset_class")[metric_col]
        .mean()
        .reset_index()
        .sort_values(metric_col, ascending=True)
    )

    fig_month = go.Figure(go.Bar(
        x=ac_month[metric_col] * 100,
        y=ac_month["asset_class"],
        orientation="h",
        marker_color=[
            THEME["positive"] if v >= 0 else THEME["negative"]
            for v in ac_month[metric_col]
        ],
        text=[f"{v*100:+.2f}%" for v in ac_month[metric_col]],
        textposition="outside",
        textfont=dict(size=10),
    ))
    fig_month.update_layout(
        paper_bgcolor=THEME["bg"], plot_bgcolor=THEME["bg"],
        font=dict(family=THEME["font"], color=THEME["text_primary"]),
        title=dict(
            text=f"Investable Asset Class Average Returns — {selected_month_name}",
            font=dict(size=13, color=THEME["text_primary"]),
        ),
        xaxis=dict(
            showgrid=True, gridcolor=THEME["border"],
            ticksuffix="%", zeroline=True, zerolinecolor=THEME["border"],
        ),
        yaxis=dict(showgrid=False, tickfont=dict(size=11)),
        margin=dict(l=20, r=80, t=50, b=20),
        height=320,
    )
    st.plotly_chart(fig_month, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 3: CUSTOM SERIES COMPARISON ──────────────────────────────────────
# User picks any combination of series — heatmap shows their seasonal patterns
# side by side for direct comparison
st.markdown('''<div class="section-header">Custom Series Comparison</div>''',
            unsafe_allow_html=True)

st.markdown(
    f'''<div class="info-card">
    Select any combination of price-return series to compare their seasonal
    patterns side by side. All values are in percentage terms and directly
    comparable. Useful for checking whether portfolio components have
    complementary or correlated seasonal patterns.
    </div>''',
    unsafe_allow_html=True
)

all_series = sorted(stats["name"].unique().tolist())

# Sensible default selection covering key Indian investor series
default_selection = [
    s for s in [
        "Nifty 50", "MCX Gold INR (Synthetic)",
        "USD/INR", "India Bond ETF", "Crude Oil Brent"
    ] if s in all_series
]

selected_custom = st.multiselect(
    "Select series to compare",
    options=all_series,
    default=default_selection,
    key="cross_custom"
)

if selected_custom:
    custom_stats = stats[stats["name"].isin(selected_custom)].copy()
    pivot_custom = custom_stats.pivot_table(
        index="name", columns="month",
        values=metric_col, aggfunc="mean"
    )
    pivot_custom = pivot_custom.reindex(columns=range(1, 13))
    pivot_custom.columns = MONTHS

    # Preserve user selection order in the heatmap rows
    pivot_custom = pivot_custom.reindex(
        [s for s in selected_custom if s in pivot_custom.index]
    )

    # Label benchmark series
    inv_map = dict(zip(meta["name"], meta["investability"]))
    pivot_custom.index = [
        f"{n} [Ref]" if inv_map.get(n) == "benchmark" else n
        for n in pivot_custom.index
    ]

    fig = build_heatmap(pivot_custom, value_col_label="Return (%)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"{len(pivot_custom)} series · all values in % terms · "
        f"[Ref] = reference benchmark · {metric_label}"
    )
else:
    st.info("Select at least one series to display the comparison heatmap.")

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown("""
**What is cross-asset analysis?**

Cross-asset analysis looks at how different types of investments —
equities, bonds, gold, currencies — behave at the same time.
Understanding whether assets move together or in opposite directions
helps build portfolios that are more resilient across market conditions.

**Why are Macro and Volatility excluded?**

GDP, CPI, unemployment and housing data are economic readings, not
investment returns. VIX and OVX are fear gauges. Mixing their monthly
changes into an investment return comparison produces meaningless
numbers. They are available on their own dedicated pages for reference.

**Why are yield and spread series excluded?**

Bond yields change by basis points (e.g. +20 bps = +0.20 percentage
points). Equity returns change by full percentages (e.g. +2%). Showing
them on the same scale makes either the equity moves look huge or the
yield moves look invisible. Yield series are shown correctly on the
Fixed Income page with basis point units and explanation.

**What does the asset class summary show?**

Each row averages all price-return series in that asset class into one
number per month. For Fixed Income, this means Bond ETF returns only
(e.g. TLT, HYG, India Bond ETF) — comparable to equity returns.

**How to use the month deep-dive**

Select an upcoming month to see which series has the strongest
historical seasonal tailwind. The winners table shows the top 10
best-performing series in that month across all years of data.

**How to use the custom comparison**

Select the series you actually hold or are considering. See whether
their seasonal patterns overlap (adding risk concentration) or
complement each other (providing diversification through the year).
""")
