
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 04_Equities.py
# PURPOSE: Detailed seasonality analysis for equity markets.
#          Covers Indian indices, global benchmarks, sector ETFs,
#          factor ETFs, thematic ETFs, and emerging market indices.
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
    page_title="Equities · Scripbox Seasonality",
    page_icon="📈",
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

# Keep only equity series
stats = stats_all[stats_all["asset_class"] == "Equity"].copy()
meta  = meta[meta["asset_class"] == "Equity"].copy()

if sig_filter == "p < 0.10":
    stats = stats[stats["p_value"] < 0.10]
elif sig_filter == "p < 0.05":
    stats = stats[stats["p_value"] < 0.05]

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Equity Markets</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Seasonal return patterns across Indian and global equity markets ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"} ·
    {metric_label}
    </div>''',
    unsafe_allow_html=True
)

# ── SUMMARY METRICS ───────────────────────────────────────────────────────────
total_eq   = meta["name"].nunique()
sig_eq     = stats[stats["p_value"] < 0.05]["name"].nunique()
dom_count  = meta[meta["investability"] == "domestic"]["name"].nunique()
intl_count = meta[
    meta["investability"].isin(["international", "international_etf"])
]["name"].nunique()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Equity Series", total_eq)
c2.metric("Significant Patterns (p<0.05)", sig_eq)
c3.metric("Indian Series", dom_count)
c4.metric("International Series", intl_count)

st.markdown("<hr>", unsafe_allow_html=True)

# ── PAGE-LEVEL FILTERS ────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Filter & Explore</div>''',
            unsafe_allow_html=True)

col_geo, col_sub, col_series = st.columns([1, 1, 2])

with col_geo:
    geo_options  = ["All"] + sorted(meta["geography"].dropna().unique().tolist())
    selected_geo = st.selectbox("Geography", geo_options, key="eq_geo")

with col_sub:
    sub_options  = ["All"] + sorted(meta["sub_class"].dropna().unique().tolist())
    selected_sub = st.selectbox("Sub-class", sub_options, key="eq_sub")

filtered_meta = meta.copy()
if selected_geo != "All":
    filtered_meta = filtered_meta[filtered_meta["geography"] == selected_geo]
if selected_sub != "All":
    filtered_meta = filtered_meta[filtered_meta["sub_class"] == selected_sub]

filtered_names = set(filtered_meta["name"].tolist())
filtered_stats = stats[stats["name"].isin(filtered_names)].copy()

with col_series:
    series_list  = sorted(filtered_stats["name"].unique().tolist())
    default_idx  = series_list.index("Nifty 50") if "Nifty 50" in series_list else 0
    selected_series = st.selectbox(
        "Select series for detail view",
        series_list, index=default_idx, key="eq_series"
    )

if filtered_stats.empty:
    st.warning("No series match the current filter combination.")
    st.stop()

# ── DETAIL BAR CHART ──────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Monthly Detail — Selected Series</div>''',
            unsafe_allow_html=True)

inv_type = filtered_meta[
    filtered_meta["name"] == selected_series
]["investability"].values
if len(inv_type) > 0 and inv_type[0] == "benchmark":
    st.markdown(
        f'''<div class="info-card">
        <strong>{selected_series}</strong> is a reference benchmark index.
        Not directly investable — accessible via ETFs or mutual funds.
        </div>''',
        unsafe_allow_html=True
    )

series_data = filtered_stats[
    filtered_stats["name"] == selected_series
].copy().sort_values("month")

fig_bar = go.Figure()

fig_bar.add_trace(go.Bar(
    x=MONTHS,
    y=series_data["avg_return"] * 100,
    name="Average Return",
    marker_color=[
        THEME["positive"] if v >= 0 else THEME["negative"]
        for v in series_data["avg_return"]
    ],
    opacity=0.85,
    text=[f"{v*100:+.2f}%" for v in series_data["avg_return"]],
    textposition="outside",
    textfont=dict(size=9),
))

fig_bar.add_trace(go.Scatter(
    x=MONTHS,
    y=series_data["median_return"] * 100,
    name="Median Return",
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
        ticksuffix="%", zeroline=True,
        zerolinecolor=THEME["border"], zerolinewidth=1.5,
    ),
    margin=dict(l=20, r=20, t=40, b=60),
    height=380,
)

st.plotly_chart(fig_bar, use_container_width=True, key="eq_detail_bar")

# ── SUPPORTING STATISTICS TABLE ───────────────────────────────────────────────
with st.expander("Show supporting statistics for selected series"):
    display_cols = ["month_name", "avg_return", "median_return",
                    "win_rate", "best_return", "best_year",
                    "worst_return", "worst_year", "n_obs", "p_value"]
    display_df = series_data[display_cols].copy()
    display_df.columns = ["Month", "Avg Return", "Median Return",
                          "Win Rate", "Best Return", "Best Year",
                          "Worst Return", "Worst Year", "Observations", "p-value"]
    for col in ["Avg Return", "Median Return", "Best Return", "Worst Return"]:
        display_df[col] = display_df[col].map(lambda x: f"{x*100:+.2f}%")
    display_df["Win Rate"]     = display_df["Win Rate"].map(
        lambda x: f"{x*100:.0f}%"
    )
    display_df["p-value"]      = display_df["p-value"].map(lambda x: f"{x:.3f}")
    display_df["Best Year"]    = display_df["Best Year"].map(
        lambda x: str(int(x)) if pd.notna(x) else ""
    )
    display_df["Worst Year"]   = display_df["Worst Year"].map(
        lambda x: str(int(x)) if pd.notna(x) else ""
    )
    display_df["Observations"] = display_df["Observations"].map(
        lambda x: str(int(x)) if pd.notna(x) else ""
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── HEATMAP SECTION ───────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Heatmap — All Equity Series</div>''',
            unsafe_allow_html=True)

SUB_CLASS_ORDER = [
    "Indian Broad Index", "Indian Size Segment", "Indian Sector Index",
    "Developed Market Index", "Emerging Market Index",
    "Sector ETF", "Factor ETF", "Thematic ETF", "Regional ETF", "Real Assets"
]

available_subs = [s for s in SUB_CLASS_ORDER
                  if s in filtered_stats["sub_class"].values]

if selected_sub != "All":
    available_subs = (
        [selected_sub] if selected_sub in available_subs else available_subs
    )

if not available_subs:
    st.info("No sub-classes available for current filter combination.")
else:
    heatmap_tabs = st.tabs(available_subs)

    for tab_idx, (htab, sub) in enumerate(zip(heatmap_tabs, available_subs)):
        with htab:
            sub_stats = filtered_stats[
                filtered_stats["sub_class"] == sub
            ].copy()

            if sub_stats.empty:
                st.info(f"No data for {sub} under current filters.")
                continue

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

            fig = build_heatmap(pivot, value_col_label="Return (%)")
            st.plotly_chart(
                fig, use_container_width=True,
                key=f"eq_heatmap_{tab_idx}_{sub.replace(' ', '_')}"
            )
            st.caption(
                f"{len(pivot)} series · {sub} · "
                f"[Ref] = reference benchmark · {metric_label}"
            )

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown("""
**What are equity seasonal patterns?**

Equity markets tend to show recurring patterns tied to earnings seasons,
budget cycles, fiscal year-ends, festive demand, and global fund flows.
For example, Indian markets often see strength around the Union Budget
(February) and ahead of Diwali. Understanding these tendencies helps
investors time entries and exits more thoughtfully.

**Indian indices vs Global benchmarks**

Indian indices like Nifty 50 and sectoral indices represent direct
investment options through index funds and ETFs available to Indian
investors. Global benchmarks like S&P 500 and Nikkei 225 are shown as
reference points — accessible through international ETFs in Global scope
or international fund-of-funds from Indian AMCs.

**Win Rate**

Win rate is the percentage of years in which the asset delivered a
positive return in that month. A win rate of 70% in January means the
index went up in 70% of all Januaries in the dataset.

**Average vs Median**

For equity markets, median is often more informative because equity
returns have fat tails — a single crash year can distort the average.
If average and median point in the same direction, the pattern is
more reliable.

**Sector ETFs and Factor ETFs (visible in Global scope)**

These are US-listed ETFs available to Indian investors under LRS or
through international fund-of-funds. Sector ETFs give exposure to
specific parts of the US economy. Factor ETFs give exposure to
investment style strategies like Momentum, Quality, Low Volatility.

**LRS — Liberalised Remittance Scheme**

Indian residents can remit up to USD 250,000 per year abroad for
investment in international stocks and ETFs. Assets marked as
international or international_etf in our database are accessible
through this route or through Indian AMC international funds.
""")
