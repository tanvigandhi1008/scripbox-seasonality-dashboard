
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 10_Scenario_Builder.py
# PURPOSE: Build a hypothetical portfolio and see its seasonal return profile.
#
# DESIGN DECISIONS:
#   - Preset portfolio section removed — presets were not working reliably
#     and the weights were indicative only. User builds from scratch.
#   - Yield, spread, rate, index series excluded from series selection —
#     these are not investable and their bps-scale values would distort
#     the weighted portfolio return calculation.
#   - Macro and Volatility excluded — not investable assets.
#   - Weight display bug fixed: normalised weights are computed and shown
#     only after the user has finished entering all weights, using a single
#     consistent pass through the data. No Streamlit rerun interference.
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
from collections import defaultdict

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Scenario Builder · Scripbox Seasonality",
    page_icon="🏗️",
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

# Apply multi-asset filter — only investable price-return series
# Yield/spread/rate/index series and Macro/Volatility classes removed
stats = filter_for_multiasset(stats_all)

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Scenario Builder</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Build a hypothetical portfolio and visualise its seasonal return profile ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"} ·
    {metric_label}
    </div>''',
    unsafe_allow_html=True
)

st.markdown(
    '''<div class="info-card">
    Select series and assign weights. The dashboard computes the weighted
    average seasonal return for each month based on historical patterns.
    Weights are normalised automatically — entering 60, 30, 10 or 6, 3, 1
    gives the same result. Only investable price-return series are available.
    This is a research tool, not a return forecast.
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── STEP 1: SELECT SERIES ─────────────────────────────────────────────────────
# Series are organised by asset class in tabs so the user can browse
# without having to know all 150+ series names in advance
st.markdown('''<div class="section-header">Step 1 — Select Series</div>''',
            unsafe_allow_html=True)

# Group investable series by asset class
meta_lookup = meta.set_index("name").to_dict("index")
all_series  = sorted(stats["name"].unique().tolist())

series_by_ac = defaultdict(list)
for s in all_series:
    ac = meta_lookup.get(s, {}).get("asset_class", "Other")
    series_by_ac[ac].append(s)

AC_ORDER = ["Equity", "Commodity", "Fixed Income", "FX", "Mutual Fund"]
available_acs = [ac for ac in AC_ORDER if ac in series_by_ac]

st.markdown(
    f'''<p style="font-size:0.875rem;color:{THEME["text_secondary"]};">
    Tick the series you want to include. Switch between asset class tabs
    to browse all available series.
    </p>''',
    unsafe_allow_html=True
)

# Use checkboxes organised by asset class tab
# Streamlit reruns on every checkbox interaction — we collect selections
# from session_state keys set by the checkboxes
ac_tabs = st.tabs(available_acs)
for ac_tab, ac in zip(ac_tabs, available_acs):
    with ac_tab:
        ac_series = sorted(series_by_ac[ac])
        cols_cb   = st.columns(3)
        for i, s in enumerate(ac_series):
            with cols_cb[i % 3]:
                st.checkbox(s, key=f"sb_cb_{s}")

# Collect all ticked series from session state
selected_series = [
    s for s in all_series
    if st.session_state.get(f"sb_cb_{s}", False)
]

st.markdown("<hr>", unsafe_allow_html=True)

# ── STEP 2: ASSIGN WEIGHTS ────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Step 2 — Assign Weights</div>''',
            unsafe_allow_html=True)

if not selected_series:
    st.info("Tick at least one series in Step 1 to continue.")
    st.stop()

st.markdown(
    f'''<p style="font-size:0.875rem;color:{THEME["text_secondary"]};">
    Enter a weight for each selected series. Any positive numbers work —
    they will be normalised automatically. Use 0 to temporarily exclude
    a series without unticking it.
    </p>''',
    unsafe_allow_html=True
)

# Equal weight default
default_w = round(100 / len(selected_series))

weight_cols = st.columns(3)
raw_weights = {}
for i, series in enumerate(selected_series):
    with weight_cols[i % 3]:
        raw_weights[series] = st.number_input(
            label=series,
            min_value=0,
            max_value=100,
            value=default_w,
            step=5,
            key=f"sb_wt_{series}"
        )

# ── STEP 3: NORMALISE AND CONFIRM ────────────────────────────────────────────
# Normalisation happens here — after ALL weight inputs have been rendered.
# This prevents the partial-rerun bug where normalisation fired with
# incomplete data while the user was still entering weights.
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('''<div class="section-header">Step 3 — Portfolio Summary</div>''',
            unsafe_allow_html=True)

total_weight = sum(raw_weights.values())

if total_weight == 0:
    st.warning("All weights are zero. Enter at least one non-zero weight.")
    st.stop()

# Normalised weights: each weight divided by the total so they sum to 1.0
# These are the actual weights used in all calculations below.
norm_weights = {
    k: v / total_weight
    for k, v in raw_weights.items()
    if v > 0
}

# Display normalised weight table — this always reflects what the user entered
weight_rows = []
for s, w in norm_weights.items():
    ac = meta_lookup.get(s, {}).get("asset_class", "—")
    weight_rows.append({
        "Series":         s,
        "Asset Class":    ac,
        "Your Weight":    raw_weights[s],
        "Normalised (%)": f"{w*100:.1f}%",
    })

st.markdown(
    f'''<p style="font-size:0.875rem;color:{THEME["text_secondary"]};">
    Your weights normalised to sum to 100%. These are the exact proportions
    used in all calculations below.
    </p>''',
    unsafe_allow_html=True
)
st.dataframe(
    pd.DataFrame(weight_rows),
    use_container_width=True, hide_index=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── STEP 4: COMPUTE PORTFOLIO SEASONAL RETURNS ────────────────────────────────
# For each month: multiply each series historical return by its normalised
# weight and sum. If a series has no data for a month, exclude it and
# rescale the remaining weights proportionally for that month only.
st.markdown('''<div class="section-header">Step 4 — Portfolio Seasonal Profile</div>''',
            unsafe_allow_html=True)

portfolio_monthly = []

for month_num in range(1, 13):
    w_avg    = 0.0
    w_median = 0.0
    w_total  = 0.0

    for series, w in norm_weights.items():
        row = stats[
            (stats["name"] == series) & (stats["month"] == month_num)
        ]
        if not row.empty and pd.notna(row["avg_return"].values[0]):
            w_avg    += row["avg_return"].values[0] * w
            w_median += row["median_return"].values[0] * w
            w_total  += w

    # Rescale if some series had no data this month
    if w_total > 0:
        w_avg    /= w_total
        w_median /= w_total

    portfolio_monthly.append({
        "month":         month_num,
        "month_name":    MONTH_FULL[month_num],
        "avg_return":    w_avg,
        "median_return": w_median,
    })

portfolio_df = pd.DataFrame(portfolio_monthly)

# Portfolio bar chart with avg bars and median line overlay
fig_port = go.Figure()

fig_port.add_trace(go.Bar(
    x=portfolio_df["month_name"],
    y=portfolio_df["avg_return"] * 100,
    name="Portfolio Average Return",
    marker_color=[
        THEME["positive"] if v >= 0 else THEME["negative"]
        for v in portfolio_df["avg_return"]
    ],
    opacity=0.85,
    text=[f"{v*100:+.2f}%" for v in portfolio_df["avg_return"]],
    textposition="outside",
    textfont=dict(size=9),
))

fig_port.add_trace(go.Scatter(
    x=portfolio_df["month_name"],
    y=portfolio_df["median_return"] * 100,
    name="Portfolio Median Return",
    mode="lines+markers",
    line=dict(color=THEME["primary"], width=2, dash="dot"),
    marker=dict(size=6, color=THEME["primary"]),
))

fig_port.update_layout(
    paper_bgcolor=THEME["bg"], plot_bgcolor=THEME["bg"],
    font=dict(family=THEME["font"], color=THEME["text_primary"]),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02,
        xanchor="right", x=1, font=dict(size=11),
    ),
    xaxis=dict(showgrid=False, tickfont=dict(size=11)),
    yaxis=dict(
        showgrid=True, gridcolor=THEME["border"],
        ticksuffix="%", zeroline=True,
        zerolinecolor=THEME["border"], zerolinewidth=1.5,
        title=dict(text="Weighted Return (%)", font=dict(size=10)),
    ),
    margin=dict(l=20, r=20, t=40, b=60),
    height=400,
)

st.plotly_chart(fig_port, use_container_width=True)

# Monthly return table
with st.expander("Show monthly portfolio return table"):
    tbl = portfolio_df[["month_name","avg_return","median_return"]].copy()
    tbl.columns = ["Month", "Avg Return", "Median Return"]
    tbl["Avg Return"]    = tbl["Avg Return"].map(lambda x: f"{x*100:+.2f}%")
    tbl["Median Return"] = tbl["Median Return"].map(lambda x: f"{x*100:+.2f}%")
    st.dataframe(tbl, use_container_width=True, hide_index=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── COMPONENT HEATMAP ─────────────────────────────────────────────────────────
# Shows each selected series individually so user can see which component
# is driving strong or weak months in the portfolio
st.markdown('''<div class="section-header">Component Series Heatmap</div>''',
            unsafe_allow_html=True)

st.markdown(
    f'''<div class="info-card">
    Each row shows the seasonal pattern of one portfolio component.
    Compare with the portfolio chart above to see which series is
    driving the portfolio's strong and weak months.
    </div>''',
    unsafe_allow_html=True
)

component_stats = stats[stats["name"].isin(list(norm_weights.keys()))].copy()

if not component_stats.empty:
    pivot_comp = component_stats.pivot_table(
        index="name", columns="month",
        values=metric_col, aggfunc="mean"
    )
    pivot_comp = pivot_comp.reindex(columns=range(1, 13))
    pivot_comp.columns = MONTHS

    # Preserve weight order — heaviest weighted series at top
    weight_order = sorted(
        norm_weights.keys(),
        key=lambda x: norm_weights[x],
        reverse=True
    )
    pivot_comp = pivot_comp.reindex(
        [s for s in weight_order if s in pivot_comp.index]
    )

    # Label benchmark series
    inv_map = dict(zip(meta["name"], meta["investability"]))
    pivot_comp.index = [
        f"{n} [Ref]" if inv_map.get(n) == "benchmark" else n
        for n in pivot_comp.index
    ]

    fig = build_heatmap(pivot_comp, value_col_label="Return (%)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"{len(pivot_comp)} components · sorted by weight (heaviest first) · "
        f"[Ref] = reference benchmark · {metric_label}"
    )

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown("""
**How the portfolio return is calculated**

For each month, the tool takes the historical average (or median) return
of each series you selected and multiplies it by that series weight.
It then sums these weighted returns to get the portfolio return for
that month. This is a weighted average of historical seasonal patterns.

**Example**

If you select Nifty 50 (weight 60%) and MCX Gold (weight 40%):
- January: Nifty 50 avg return = +2.0%, Gold avg return = +1.5%
- Portfolio January = (2.0% × 0.60) + (1.5% × 0.40) = 1.80%

**Why are weights normalised?**

Normalisation means the weights always sum to 100% regardless of what
numbers you enter. Entering 60 and 40 gives the same result as entering
6 and 4, or 3 and 2. Only the relative proportion matters.

**What happens if a series has no data for a month?**

If a series has no historical data for a particular month, it is
excluded from that month's calculation and the remaining weights are
rescaled proportionally. The portfolio return for that month reflects
only the series that have data.

**Why are yield and macro series excluded?**

Yield series (bond yields, credit spreads) are stored in basis points,
not percentage returns. Including them in a weighted portfolio return
would mix incompatible units — a 20 bps yield move weighted alongside
a 2% equity return produces a meaningless number. Only price-return
series are included so all weighted returns are in comparable % terms.

**How to use this for portfolio planning**

Look at the monthly bar chart. Identify your portfolio's weakest
seasonal months. Then look at the component heatmap to find which
series is dragging those months down. You can then decide whether to
reduce that allocation or add a series that historically performs well
in those months to smooth out the seasonal profile.
""")
