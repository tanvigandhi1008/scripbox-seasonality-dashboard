
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 12_Current_Year.py
# PURPOSE: Compares actual year-to-date returns in the current year against
#          historical seasonal averages. Answers: "Is this year following
#          its seasonal pattern or not?"
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
    page_title="Current Year · Scripbox Seasonality",
    page_icon="📆",
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
monthly_rets    = load_monthly_returns(currency)

if sig_filter == "p < 0.10":
    stats_all = stats_all[stats_all["p_value"] < 0.10]
elif sig_filter == "p < 0.05":
    stats_all = stats_all[stats_all["p_value"] < 0.05]

# Apply multi-asset filter for price-return series only
# Yield series cannot be compared to price returns on a deviation chart
stats = filter_for_multiasset(stats_all)

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# ── CURRENT YEAR SETUP ────────────────────────────────────────────────────────
current_year     = datetime.today().year
current_month    = datetime.today().month
completed_months = current_month - 1

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Current Year vs Historical</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    How {current_year} returns compare to historical seasonal averages ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"} ·
    {metric_label}
    </div>''',
    unsafe_allow_html=True
)

if completed_months == 0:
    st.info(
        f"No completed months yet in {current_year}. "
        f"This page updates as each month closes."
    )
    st.stop()

st.markdown(
    f'''<div class="info-card">
    Showing data for the first <strong>{completed_months} completed
    month{"s" if completed_months > 1 else ""}</strong> of {current_year}.
    The current month ({MONTH_FULL[current_month]}) is excluded as it is
    still in progress. Green deviation = outperforming historical average.
    Red deviation = underperforming. Only price-return series shown.
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── EXTRACT CURRENT YEAR RETURNS ──────────────────────────────────────────────
visible_series = set(meta["name"].tolist())
# Further filter to price-return series only (exclude yield/spread)
price_series_names = set(stats["name"].tolist())

current_year_rets = monthly_rets[
    monthly_rets.index.year == current_year
].copy()
current_year_rets = current_year_rets[
    current_year_rets.index.month <= completed_months
]

available_cols = [
    c for c in current_year_rets.columns
    if c in visible_series and c in price_series_names
]
current_year_rets = current_year_rets[available_cols]

if current_year_rets.empty:
    st.warning(
        f"No current year data found for {current_year}. "
        "The monthly returns file may not yet include this year."
    )
    st.stop()

# ── SERIES SELECTOR ───────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Series Detail View</div>''',
            unsafe_allow_html=True)

col_ac, col_series = st.columns([1, 2])

with col_ac:
    ac_options  = ["All"] + sorted(
        meta[meta["name"].isin(available_cols)]["asset_class"].unique().tolist()
    )
    selected_ac = st.selectbox("Asset Class", ac_options, key="cy_ac")

if selected_ac != "All":
    ac_series            = meta[meta["asset_class"] == selected_ac]["name"].tolist()
    available_for_select = [s for s in available_cols if s in ac_series]
else:
    available_for_select = available_cols

available_for_select = sorted(available_for_select)

with col_series:
    default_name = "Nifty 50"
    default_idx  = (
        available_for_select.index(default_name)
        if default_name in available_for_select else 0
    )
    selected_series = st.selectbox(
        "Select series", available_for_select,
        index=default_idx, key="cy_series"
    )

# ── SINGLE SERIES CHART ───────────────────────────────────────────────────────
series_current = (
    current_year_rets[selected_series].dropna()
    if selected_series in current_year_rets.columns
    else pd.Series()
)
series_hist = stats[stats["name"] == selected_series].sort_values("month")

comparison_rows = []
for month_num in range(1, completed_months + 1):
    actual_row = series_current[series_current.index.month == month_num]
    hist_row   = series_hist[series_hist["month"] == month_num]

    actual_val = actual_row.values[0] if not actual_row.empty else np.nan
    hist_avg   = hist_row["avg_return"].values[0] if not hist_row.empty else np.nan
    hist_med   = hist_row["median_return"].values[0] if not hist_row.empty else np.nan

    comparison_rows.append({
        "month":       month_num,
        "month_name":  MONTH_FULL[month_num],
        "actual":      actual_val,
        "hist_avg":    hist_avg,
        "hist_median": hist_med,
        "deviation":   (actual_val - hist_avg)
                       if pd.notna(actual_val) and pd.notna(hist_avg) else np.nan,
    })

comparison_df = pd.DataFrame(comparison_rows)

if not comparison_df.empty and not comparison_df["actual"].isna().all():

    fig_cy = go.Figure()

    fig_cy.add_trace(go.Bar(
        x=comparison_df["month_name"],
        y=comparison_df["actual"] * 100,
        name=f"{current_year} Actual",
        marker_color=[
            THEME["positive"] if v >= 0 else THEME["negative"]
            for v in comparison_df["actual"].fillna(0)
        ],
        opacity=0.85,
        text=[
            f"{v*100:+.2f}%" if pd.notna(v) else ""
            for v in comparison_df["actual"]
        ],
        textposition="outside",
        textfont=dict(size=9),
    ))

    fig_cy.add_trace(go.Scatter(
        x=comparison_df["month_name"],
        y=comparison_df["hist_avg"] * 100,
        name=f"Historical {metric_label}",
        mode="lines+markers",
        line=dict(color=THEME["primary"], width=2, dash="dot"),
        marker=dict(size=6, color=THEME["primary"]),
    ))

    fig_cy.add_trace(go.Scatter(
        x=comparison_df["month_name"],
        y=comparison_df["hist_median"] * 100,
        name="Historical Median",
        mode="lines+markers",
        line=dict(color=THEME["text_secondary"], width=1.5, dash="dash"),
        marker=dict(size=5, color=THEME["text_secondary"]),
    ))

    fig_cy.update_layout(
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
        height=400,
        title=dict(
            text=f"{selected_series} — {current_year} vs Historical",
            font=dict(size=13, color=THEME["text_primary"]),
        ),
    )
    st.plotly_chart(fig_cy, use_container_width=True, key="cy_detail_chart")

    with st.expander(f"Show deviation table for {selected_series}"):
        dev_df = comparison_df[[
            "month_name", "actual", "hist_avg", "hist_median", "deviation"
        ]].copy()
        dev_df.columns = [
            "Month", f"{current_year} Actual",
            "Historical Avg", "Historical Median", "Deviation from Avg"
        ]
        for col in [f"{current_year} Actual", "Historical Avg",
                    "Historical Median", "Deviation from Avg"]:
            dev_df[col] = dev_df[col].map(
                lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—"
            )
        st.dataframe(dev_df, use_container_width=True, hide_index=True)
else:
    st.info(f"No current year data available for {selected_series}.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── DEVIATION HEATMAP ─────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">All Series — Deviation from Historical Average</div>''',
            unsafe_allow_html=True)

st.markdown(
    f'''<div class="info-card">
    Each cell shows how much each series is deviating from its historical
    {metric_label.lower()} for each completed month of {current_year}.
    Green = outperforming history. Red = underperforming history.
    </div>''',
    unsafe_allow_html=True
)

deviation_rows = []
for series in available_cols:
    for month_num in range(1, completed_months + 1):
        actual_series = (
            current_year_rets[series]
            if series in current_year_rets.columns
            else pd.Series()
        )
        actual_vals = actual_series[actual_series.index.month == month_num]
        actual_val  = actual_vals.values[0] if not actual_vals.empty else np.nan

        hist_row = stats[
            (stats["name"] == series) & (stats["month"] == month_num)
        ]
        hist_val = hist_row[metric_col].values[0] if not hist_row.empty else np.nan

        if pd.notna(actual_val) and pd.notna(hist_val):
            deviation_rows.append({
                "name":      series,
                "month":     month_num,
                "deviation": actual_val - hist_val,
            })

if deviation_rows:
    dev_df_all = pd.DataFrame(deviation_rows)

    if selected_ac != "All":
        ac_names   = meta[meta["asset_class"] == selected_ac]["name"].tolist()
        dev_df_all = dev_df_all[dev_df_all["name"].isin(ac_names)]

    if not dev_df_all.empty:
        pivot_dev = dev_df_all.pivot_table(
            index="name", columns="month",
            values="deviation", aggfunc="mean"
        )
        pivot_dev = pivot_dev.reindex(
            columns=range(1, completed_months + 1)
        )
        pivot_dev.columns = MONTHS[:completed_months]

        inv_map = dict(zip(meta["name"], meta["investability"]))
        pivot_dev.index = [
            f"{n} [Ref]" if inv_map.get(n) == "benchmark" else n
            for n in pivot_dev.index
        ]

        fig_dev = build_heatmap(
            pivot_dev,
            value_col_label="Deviation (%)",
        )
        st.plotly_chart(
            fig_dev, use_container_width=True, key="cy_deviation_heatmap"
        )
        st.caption(
            f"Deviation = {current_year} actual minus historical "
            f"{metric_label.lower()} · "
            f"{completed_months} completed months · "
            f"[Ref] = reference benchmark"
        )
    else:
        st.info("No deviation data for current filter combination.")
else:
    st.info(f"No current year vs historical data for {current_year}.")

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown(f"""
**What does this page show?**

This page compares what has actually happened in {current_year} against
what history would have predicted based on seasonal averages. It answers:
is this year following its usual seasonal pattern, or is something
different happening?

**How to interpret the deviation heatmap**

Each cell = actual return minus historical average for that series
in that month:
- Green = outperformed historical seasonal average
- Red = underperformed historical seasonal average

**Why does this matter?**

Large deviations from seasonal norms can signal:
- A structural change in market dynamics
- A macro event that overrode seasonal patterns
- Mean reversion potential for subsequent months

**Current month exclusion**

The current month is always excluded because it has not yet closed.
Including a partial month would distort the comparison.

**Yield series excluded**

Yield and spread series are excluded from this page because their
monthly changes are in basis points, not percentage returns. Mixing
them with equity and commodity returns on the same deviation scale
would produce meaningless comparisons.
""")
