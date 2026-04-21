
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 06_Commodities.py
# PURPOSE: Seasonal patterns across commodity markets including precious
#          metals, energy, base metals, and agriculture.
#          MCX Gold INR (Synthetic) is the default series.
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
    page_title="Commodities · Scripbox Seasonality",
    page_icon="🥇",
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

stats = stats_all[stats_all["asset_class"] == "Commodity"].copy()
meta  = meta[meta["asset_class"] == "Commodity"].copy()

if sig_filter == "p < 0.10":
    stats = stats[stats["p_value"] < 0.10]
elif sig_filter == "p < 0.05":
    stats = stats[stats["p_value"] < 0.05]

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Commodities</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Seasonal return patterns across precious metals, energy, base metals,
    and agriculture · {scope} scope ·
    {"INR" if currency == "inr" else "Local Currency"} · {metric_label}
    </div>''',
    unsafe_allow_html=True
)

# ── SUMMARY METRICS ───────────────────────────────────────────────────────────
total_comm  = meta["name"].nunique()
sig_comm    = stats[stats["p_value"] < 0.05]["name"].nunique()
dom_count   = meta[meta["investability"] == "domestic"]["name"].nunique()
intl_count  = meta[
    meta["investability"].isin(["international", "international_etf"])
]["name"].nunique()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Commodity Series", total_comm)
c2.metric("Significant Patterns (p<0.05)", sig_comm)
c3.metric("Domestic / MCX Series", dom_count)
c4.metric("International Series", intl_count)

st.markdown("<hr>", unsafe_allow_html=True)

# ── PAGE-LEVEL FILTERS ────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Filter & Explore</div>''',
            unsafe_allow_html=True)

col_grp, col_series = st.columns([1, 2])

with col_grp:
    grp_options  = ["All"] + sorted(meta["sub_class"].dropna().unique().tolist())
    selected_grp = st.selectbox("Commodity Group", grp_options, key="comm_grp")

filtered_meta = meta.copy()
if selected_grp != "All":
    filtered_meta = filtered_meta[filtered_meta["sub_class"] == selected_grp]

filtered_names = set(filtered_meta["name"].tolist())
filtered_stats = stats[stats["name"].isin(filtered_names)].copy()

with col_series:
    series_list = sorted(filtered_stats["name"].unique().tolist())
    if "MCX Gold INR (Synthetic)" in series_list:
        default_idx = series_list.index("MCX Gold INR (Synthetic)")
    elif "Gold" in series_list:
        default_idx = series_list.index("Gold")
    else:
        default_idx = 0
    selected_series = st.selectbox(
        "Select series for detail view",
        series_list, index=default_idx, key="comm_series"
    )

if filtered_stats.empty:
    st.warning("No series match the current filter combination.")
    st.stop()

# ── SYNTHETIC NOTE ────────────────────────────────────────────────────────────
series_notes = filtered_meta[
    filtered_meta["name"] == selected_series
]["notes"].values

if len(series_notes) > 0 and pd.notna(series_notes[0]):
    if "synthetic" in str(series_notes[0]).lower():
        st.markdown(
            f'''<div class="synthetic-note">
            <strong>Data note — {selected_series}:</strong> Synthetically
            constructed from international USD prices converted to INR using
            USD/INR exchange rates. Approximates what an Indian investor
            holding this commodity experiences in rupee terms.
            </div>''',
            unsafe_allow_html=True
        )

# ── DETAIL BAR CHART ──────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Monthly Detail — Selected Series</div>''',
            unsafe_allow_html=True)

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

st.plotly_chart(fig_bar, use_container_width=True, key="comm_detail_bar")

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
st.markdown('''<div class="section-header">Heatmap — All Commodity Series</div>''',
            unsafe_allow_html=True)

SUB_CLASS_ORDER = [
    "Precious Metal", "Energy", "Base Metal", "Agriculture", "Commodity Index"
]

available_subs = [s for s in SUB_CLASS_ORDER
                  if s in filtered_stats["sub_class"].values]

if selected_grp != "All":
    available_subs = (
        [selected_grp] if selected_grp in available_subs else available_subs
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
                key=f"comm_heatmap_{tab_idx}_{sub.replace(' ', '_')}"
            )
            st.caption(
                f"{len(pivot)} series · {sub} · "
                f"[Ref] = reference benchmark · {metric_label}"
            )

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown("""
**Why do commodities matter for Indian investors?**

India is one of the world's largest consumers of gold and a major
importer of crude oil. Commodity prices directly affect inflation,
the current account deficit, and the rupee. Understanding seasonal
patterns in commodities helps investors hedge currency risk, time
gold purchases, and anticipate energy cost cycles.

**Gold — the most important commodity for Indian investors**

Gold has deep cultural significance in India and is also a financial
asset used for portfolio protection. Gold prices tend to have seasonal
patterns driven by Indian festival and wedding seasons (September to
November), Chinese New Year demand, and global risk-off episodes.
MCX Gold INR (Synthetic) shows the combined effect of gold prices
and the rupee — what an Indian investor actually experiences.

**MCX Synthetic series — what this means**

Direct MCX historical price data is not freely available via public
APIs. We construct these series from international USD spot prices
converted to INR using USD/INR exchange rates. This captures the
real experience of an Indian investor holding these commodities.
The synthetic flag is shown explicitly whenever such a series is selected.

**Crude oil and India**

India imports approximately 85% of its crude oil needs. Rising crude
prices pressure the trade deficit and the rupee. Brent crude is the
international benchmark most relevant to Indian oil pricing.
WTI crude is the US benchmark — also shown for reference.

**Base metals as economic indicators**

Copper is sometimes called Dr. Copper because its price tracks global
economic health closely. Rising copper prices signal expanding
industrial activity worldwide.

**Commodity Index ETFs (visible in Global scope)**

These ETFs give diversified exposure to a basket of commodities.
Available through LRS for Indian investors seeking commodity
diversification beyond gold.
""")
