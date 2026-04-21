
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 07_Currencies.py
# PURPOSE: Seasonal patterns in foreign exchange markets.
#          INR crosses are most relevant for Indian investors.
#          FX series always use local currency stats — converting
#          exchange rates to INR does not make conceptual sense.
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
    page_title="Currencies · Scripbox Seasonality",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
render_sidebar()

# ── READ CONTROLS ─────────────────────────────────────────────────────────────
scope          = st.session_state.get("market_scope", "Domestic")
# FX is always shown in local currency terms regardless of sidebar toggle
# Converting an exchange rate to INR is not meaningful
sig_filter     = st.session_state.get("sig_filter", "All patterns")
lookback       = st.session_state.get("lookback_years", 25)
heatmap_metric = st.session_state.get("heatmap_metric", "Average Return")

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
# Force local currency for FX regardless of user selection
stats_all, meta = prepare_stats("local", scope, lookback)

stats = stats_all[stats_all["asset_class"] == "FX"].copy()
meta  = meta[meta["asset_class"] == "FX"].copy()

if sig_filter == "p < 0.10":
    stats = stats[stats["p_value"] < 0.10]
elif sig_filter == "p < 0.05":
    stats = stats[stats["p_value"] < 0.05]

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Currencies</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Seasonal patterns in exchange rates · {scope} scope ·
    Local Currency (FX always shown in native terms) · {metric_label}
    </div>''',
    unsafe_allow_html=True
)

st.markdown(
    f'''<div class="info-card">
    Currency pairs are always shown in their native terms regardless of
    the Currency View setting in the sidebar. For USD/INR, a positive
    return means the rupee weakened (more rupees per dollar). A negative
    return means the rupee strengthened.
    </div>''',
    unsafe_allow_html=True
)

# ── SUMMARY METRICS ───────────────────────────────────────────────────────────
total_fx   = meta["name"].nunique()
sig_fx     = stats[stats["p_value"] < 0.05]["name"].nunique()
inr_count  = meta[meta["investability"] == "domestic"]["name"].nunique()
intl_count = meta[meta["investability"] == "international"]["name"].nunique()

c1, c2, c3, c4 = st.columns(4)
c1.metric("FX Series", total_fx)
c2.metric("Significant Patterns (p<0.05)", sig_fx)
c3.metric("INR Cross Pairs", inr_count)
c4.metric("International Pairs", intl_count)

st.markdown("<hr>", unsafe_allow_html=True)

# ── PAGE-LEVEL FILTERS ────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Filter & Explore</div>''',
            unsafe_allow_html=True)

col_grp, col_series = st.columns([1, 2])

with col_grp:
    available_grps = ["All"] + [
        g for g in ["INR Cross", "Major Pair", "EM Pair", "Dollar Index"]
        if g in meta["sub_class"].values
    ]
    selected_grp = st.selectbox("FX Group", available_grps, key="fx_grp")

filtered_meta = meta.copy()
if selected_grp != "All":
    filtered_meta = filtered_meta[filtered_meta["sub_class"] == selected_grp]

filtered_names = set(filtered_meta["name"].tolist())
filtered_stats = stats[stats["name"].isin(filtered_names)].copy()

with col_series:
    series_list  = sorted(filtered_stats["name"].unique().tolist())
    default_name = "USD/INR"
    default_idx  = series_list.index(default_name) if default_name in series_list else 0
    selected_series = st.selectbox(
        "Select series for detail view",
        series_list, index=default_idx, key="fx_series"
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
        <strong>{selected_series}</strong> is a reference benchmark.
        The DXY Dollar Index measures the US dollar against a basket
        of major currencies. It signals the overall strength of the
        dollar, which affects all INR crosses and international
        investment returns for Indian investors.
        </div>''',
        unsafe_allow_html=True
    )

if selected_series == "USD/INR":
    st.markdown(
        f'''<div class="info-card">
        For <strong>USD/INR</strong>: positive return = rupee weakened
        (USD became more expensive). Negative = rupee strengthened.
        Rupee weakening raises the cost of international investments
        and imports for Indian investors.
        </div>''',
        unsafe_allow_html=True
    )

series_data = filtered_stats[
    filtered_stats["name"] == selected_series
].copy().sort_values("month")

fig_bar = go.Figure()

# For USD/INR: positive = rupee weakened = bad for Indian investors = red
# For other pairs: standard green/red
is_inr_pair = "INR" in selected_series and selected_series.startswith("USD")

fig_bar.add_trace(go.Bar(
    x=MONTHS,
    y=series_data["avg_return"] * 100,
    name="Average Return",
    marker_color=[
        (THEME["negative"] if v >= 0 else THEME["positive"])
        if is_inr_pair
        else (THEME["positive"] if v >= 0 else THEME["negative"])
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

st.plotly_chart(fig_bar, use_container_width=True, key="fx_detail_bar")

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
st.markdown('''<div class="section-header">Heatmap — All Currency Pairs</div>''',
            unsafe_allow_html=True)

# INR crosses first — most relevant to Indian investors
SUB_CLASS_ORDER = ["INR Cross", "Major Pair", "EM Pair", "Dollar Index"]

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
                key=f"fx_heatmap_{tab_idx}_{sub.replace(' ', '_')}"
            )
            st.caption(
                f"{len(pivot)} series · {sub} · "
                f"Positive = quote currency weakened · "
                f"[Ref] = reference benchmark · {metric_label}"
            )

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown("""
**Why do exchange rates matter for Indian investors?**

Every international investment an Indian makes is ultimately in rupee
terms. If you invest in a US ETF and the dollar weakens against the
rupee, your returns in INR terms are lower even if the US investment
did well. Understanding rupee seasonality helps investors decide when
to deploy funds internationally.

**How to read FX returns**

For USD/INR: positive return = dollar strengthened = rupee weakened.
For EUR/USD: positive return = euro strengthened against dollar.

For INR cross pairs (USD/INR, EUR/INR etc.):
- Positive = rupee weakened = international investments more expensive
  but existing foreign holdings gain in INR terms
- Negative = rupee strengthened = international investments cheaper
  but existing holdings lose in INR terms

**INR Cross pairs — most relevant for Indian investors**

These pairs show how the rupee moves against major world currencies.
USD/INR is the most important as most international assets are priced
in dollars. EUR/INR matters for European exposure and travel.
JPY/INR is relevant for Japan-linked funds.

**DXY Dollar Index**

Measures the US dollar against a basket of six major currencies.
A rising DXY is generally negative for emerging markets including
India because it tightens global dollar liquidity.

**Why is currency not converted to INR on this page?**

Converting exchange rates to INR would produce meaningless numbers.
An exchange rate is already a ratio between two currencies. The INR
toggle applies to asset return series (equities, bonds, commodities)
to show what Indian investors earned in rupee terms. For FX pairs,
the native quote is always the correct view.
""")
