
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 13_Decade_Breakdown.py
# PURPOSE: Breaks down seasonal patterns by decade to show whether patterns
#          are stable over time or have shifted. A pattern that holds across
#          multiple decades is more reliable than one driven by a single period.
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
    page_title="Decade Breakdown · Scripbox Seasonality",
    page_icon="📊",
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

# Apply multi-asset filter — price-return series only
# Yield and spread series excluded so colour scales are comparable
stats = filter_for_multiasset(stats_all)

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# Keep only price-return series in monthly returns
visible_price = set(stats["name"].tolist())
available_cols = [
    c for c in monthly_rets.columns if c in visible_price
]
monthly_rets = monthly_rets[available_cols]

# ── DECADE DEFINITIONS ────────────────────────────────────────────────────────
current_year = datetime.today().year
DECADES = {
    "2000s (2000–2009)":              (2000, 2009),
    "2010s (2010–2019)":              (2010, 2019),
    f"2020s (2020–{current_year})":   (2020, current_year),
}

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Decade Breakdown</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    How seasonal patterns have evolved across decades ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"} ·
    {metric_label}
    </div>''',
    unsafe_allow_html=True
)

st.markdown(
    '''<div class="info-card">
    A seasonal pattern that holds consistently across the 2000s, 2010s,
    and 2020s is far more reliable than one that only appeared in a
    single decade. Use this page to test the robustness of any pattern
    you find elsewhere in the dashboard.
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── SERIES SELECTOR ───────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Select Series for Decade Analysis</div>''',
            unsafe_allow_html=True)

col_ac, col_series = st.columns([1, 2])

with col_ac:
    ac_options  = ["All"] + sorted(meta["asset_class"].unique().tolist())
    selected_ac = st.selectbox("Asset Class", ac_options, key="dec_ac")

if selected_ac != "All":
    ac_names          = meta[meta["asset_class"] == selected_ac]["name"].tolist()
    series_for_select = [s for s in available_cols if s in ac_names]
else:
    series_for_select = available_cols

series_for_select = sorted(series_for_select)

with col_series:
    default_name = "Nifty 50"
    default_idx  = (
        series_for_select.index(default_name)
        if default_name in series_for_select else 0
    )
    selected_series = st.selectbox(
        "Select series", series_for_select,
        index=default_idx, key="dec_series"
    )

# ── HELPER: COMPUTE DECADE STATS ─────────────────────────────────────────────
def compute_decade_stats(series_name, year_start, year_end, returns_df):
    if series_name not in returns_df.columns:
        return pd.DataFrame()
    mask    = (
        (returns_df.index.year >= year_start) &
        (returns_df.index.year <= year_end)
    )
    dec_ret = returns_df.loc[mask, series_name].dropna()
    if dec_ret.empty:
        return pd.DataFrame()
    rows = []
    for month_num in range(1, 13):
        month_vals = dec_ret[dec_ret.index.month == month_num]
        if len(month_vals) >= 2:
            rows.append({
                "month":         month_num,
                "month_name":    MONTH_FULL[month_num],
                "avg_return":    month_vals.mean(),
                "median_return": month_vals.median(),
                "win_rate":      (month_vals > 0).mean(),
                "n_obs":         len(month_vals),
            })
    return pd.DataFrame(rows)

# ── SINGLE SERIES DECADE COMPARISON ──────────────────────────────────────────
st.markdown('''<div class="section-header">Decade-by-Decade Monthly Returns</div>''',
            unsafe_allow_html=True)

decade_data = {}
for dec_label, (yr_start, yr_end) in DECADES.items():
    dec_stats = compute_decade_stats(
        selected_series, yr_start, yr_end, monthly_rets
    )
    if not dec_stats.empty:
        decade_data[dec_label] = dec_stats

if not decade_data:
    st.info(
        f"Insufficient data for {selected_series} to perform decade breakdown."
    )
else:
    dec_cols = st.columns(len(decade_data))
    display_col = (
        "avg_return" if heatmap_metric == "Average Return"
        else "median_return"
    )

    for col_idx, (col, (dec_label, dec_stats)) in enumerate(
        zip(dec_cols, decade_data.items())
    ):
        with col:
            fig_dec = go.Figure()
            fig_dec.add_trace(go.Bar(
                x=dec_stats["month_name"],
                y=dec_stats[display_col] * 100,
                marker_color=[
                    THEME["positive"] if v >= 0 else THEME["negative"]
                    for v in dec_stats[display_col]
                ],
                text=[f"{v*100:+.1f}%" for v in dec_stats[display_col]],
                textposition="outside",
                textfont=dict(size=7),
                name=dec_label,
            ))
            fig_dec.update_layout(
                paper_bgcolor=THEME["bg"], plot_bgcolor=THEME["bg"],
                font=dict(family=THEME["font"], color=THEME["text_primary"],
                          size=10),
                title=dict(
                    text=dec_label,
                    font=dict(size=11, color=THEME["text_primary"]),
                ),
                xaxis=dict(showgrid=False, tickfont=dict(size=8),
                           tickangle=45),
                yaxis=dict(
                    showgrid=True, gridcolor=THEME["border"],
                    ticksuffix="%", zeroline=True,
                    zerolinecolor=THEME["border"],
                ),
                margin=dict(l=10, r=10, t=40, b=60),
                height=320,
                showlegend=False,
            )
            st.plotly_chart(
                fig_dec, use_container_width=True,
                key=f"dec_bar_{col_idx}_{dec_label.replace(' ','_')}"
            )
            n_years = (
                yr_end - yr_start + 1
                if dec_label != list(decade_data.keys())[-1]
                else current_year - 2020 + 1
            )
            st.caption(f"~{n_years} years · {metric_label}")

st.markdown("<hr>", unsafe_allow_html=True)

# ── DECADE CONSISTENCY HEATMAP ────────────────────────────────────────────────
st.markdown('''<div class="section-header">Decade Consistency Heatmap</div>''',
            unsafe_allow_html=True)

st.markdown(
    f'''<div class="info-card">
    Each row is one decade. Consistent colour across all rows signals a
    robust seasonal pattern. Colour that flips between decades signals
    an unstable or regime-dependent pattern.
    </div>''',
    unsafe_allow_html=True
)

if decade_data:
    display_col = (
        "avg_return" if heatmap_metric == "Average Return"
        else "median_return"
    )
    dec_pivot_rows = {}
    for dec_label, dec_stats in decade_data.items():
        month_vals = dec_stats.set_index("month")[display_col]
        dec_pivot_rows[dec_label] = [
            month_vals.get(m, np.nan) for m in range(1, 13)
        ]

    dec_pivot = pd.DataFrame(dec_pivot_rows, index=MONTHS).T

    fig_dec_hm = build_heatmap(
        dec_pivot,
        value_col_label="Return (%)",
        height=max(200, len(dec_pivot) * 60 + 80)
    )
    st.plotly_chart(
        fig_dec_hm, use_container_width=True,
        key="dec_consistency_heatmap"
    )
    st.caption(
        f"{selected_series} · {metric_label} by decade · "
        "Consistent colour across rows = robust pattern"
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ── ALL SERIES BY DECADE ──────────────────────────────────────────────────────
st.markdown('''<div class="section-header">All Series by Decade</div>''',
            unsafe_allow_html=True)

all_decade_pivots = {}
display_col = (
    "avg_return" if heatmap_metric == "Average Return"
    else "median_return"
)

for dec_label, (yr_start, yr_end) in DECADES.items():
    pivot_rows = {}
    for series in available_cols:
        dec_stats = compute_decade_stats(
            series, yr_start, yr_end, monthly_rets
        )
        if not dec_stats.empty:
            month_vals    = dec_stats.set_index("month")[display_col]
            pivot_rows[series] = [
                month_vals.get(m, np.nan) for m in range(1, 13)
            ]

    if pivot_rows:
        df_pivot = pd.DataFrame(pivot_rows, index=MONTHS).T
        if selected_ac != "All":
            ac_names = meta[meta["asset_class"] == selected_ac]["name"].tolist()
            df_pivot = df_pivot[df_pivot.index.isin(ac_names)]
        if not df_pivot.empty:
            all_decade_pivots[dec_label] = df_pivot

if all_decade_pivots:
    dec_tabs = st.tabs(list(all_decade_pivots.keys()))
    for dtab_idx, (dtab, (dec_label, dpivot)) in enumerate(
        zip(dec_tabs, all_decade_pivots.items())
    ):
        with dtab:
            inv_map = dict(zip(meta["name"], meta["investability"]))
            dpivot.index = [
                f"{n} [Ref]" if inv_map.get(n) == "benchmark" else n
                for n in dpivot.index
            ]
            fig = build_heatmap(dpivot, value_col_label="Return (%)")
            st.plotly_chart(
                fig, use_container_width=True,
                key=f"dec_all_{dtab_idx}_{dec_label.replace(' ','_')}"
            )
            st.caption(
                f"{len(dpivot)} series · {dec_label} · "
                f"[Ref] = reference benchmark · {metric_label}"
            )
else:
    st.info("Insufficient data to build decade heatmaps for current filters.")

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown("""
**Why break patterns down by decade?**

Seasonal patterns can emerge, strengthen, weaken, or disappear over
time as market structure, investor behaviour, and macro regimes change.
A pattern observed only in the 2000s may be explained by a specific
economic cycle from that era rather than a genuine recurring tendency.

**What makes a pattern robust?**

A pattern is considered robust if it appears in the same direction
across at least two of the three decades with broadly similar magnitude.

**How to use the consistency heatmap**

Look at the consistency heatmap for your selected series. If you see
green in January across all three decades, the January effect is robust.
If January is green in the 2000s but red in the 2020s, the pattern has
broken down and should not be relied upon.

**Why does the 2020s decade have fewer observations?**

The 2020s only includes years from 2020 to the current year, giving
fewer data points. Patterns in the 2020s tab should be interpreted
with more caution than those in the 2000s and 2010s tabs.

**Structural breaks**

Sometimes a pattern changes sharply between decades due to a permanent
change in how a market works — for example India's inclusion in global
bond indices, changes in RBI policy framework, or the shift to
algorithmic trading. If you notice a clear break between decades,
investigate what macro event may have caused it.
""")
