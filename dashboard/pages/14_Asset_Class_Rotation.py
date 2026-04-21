
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 14_Asset_Class_Rotation.py
# PURPOSE: Shows which investable asset classes lead and lag in each month.
#
# FILTERING RULES:
#   - Macro and Volatility excluded — not investable, distort averages
#   - Yield and spread series excluded from Fixed Income averaging —
#     their bps-scale changes would dominate and distort the class average
#   - Only Bond ETF price returns represent Fixed Income in rotation views
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st


from utils.data_loader import (
    load_metadata, load_seasonality_stats,
    filter_by_market_scope, render_sidebar, inject_css,
    build_heatmap, prepare_stats, filter_for_multiasset,
    THEME, MONTHS, MONTH_FULL, HEATMAP_COLORSCALE
)
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Asset Class Rotation · Scripbox Seasonality",
    page_icon="🔄",
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
# and removes Macro and Volatility. All remaining are price-return series.
stats = filter_for_multiasset(stats_all)

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# Investable asset classes for rotation analysis
# Fixed Income here = Bond ETFs only (yield series already removed by filter)
ROTATION_CLASSES = ["Equity", "Fixed Income", "Commodity", "FX", "Mutual Fund"]

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Asset Class Rotation</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Which investable asset classes lead and lag in each month ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"} ·
    {metric_label}
    </div>''',
    unsafe_allow_html=True
)

st.markdown(
    '''<div class="info-card">
    Asset class rotation describes the tendency for capital to flow from one
    type of investment to another as the year progresses. All values are in
    percentage terms (price returns only). Fixed Income represents Bond ETF
    returns — yield series are excluded so units are comparable across classes.
    Macro indicators and Volatility indices are excluded as they are not
    investable assets.
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 1: MONTHLY ROTATION RANKING HEATMAP ──────────────────────────────
# For each month, ranks all investable asset classes from best to worst
st.markdown('''<div class="section-header">Monthly Asset Class Rankings</div>''',
            unsafe_allow_html=True)

st.markdown(
    f'''<div class="info-card">
    Each cell shows the rank (#1 = best) and {metric_label.lower()} for that
    asset class in that month. Colour intensity shows return magnitude.
    All values are price returns in percentage terms.
    </div>''',
    unsafe_allow_html=True
)

# Filter stats to rotation classes only
rotation_stats = stats[stats["asset_class"].isin(ROTATION_CLASSES)].copy()

# Compute average return per asset class per month
ac_monthly_avg = (
    rotation_stats
    .groupby(["asset_class", "month"])[metric_col]
    .mean()
    .reset_index()
)

# Build ranking for each month
ranking_rows = []
for month_num in range(1, 13):
    month_data = ac_monthly_avg[ac_monthly_avg["month"] == month_num].copy()
    month_data = month_data.sort_values(metric_col, ascending=False)
    month_data["rank"]       = range(1, len(month_data) + 1)
    month_data["month_name"] = MONTH_FULL[month_num]
    ranking_rows.append(month_data)

ranking_df = pd.concat(ranking_rows, ignore_index=True) if ranking_rows else pd.DataFrame()

if not ranking_df.empty:
    pivot_rank_val  = ranking_df.pivot(
        index="asset_class", columns="month", values=metric_col
    )
    pivot_rank_text = ranking_df.pivot(
        index="asset_class", columns="month", values="rank"
    )

    pivot_rank_val  = pivot_rank_val.reindex(columns=range(1, 13))
    pivot_rank_text = pivot_rank_text.reindex(columns=range(1, 13))
    pivot_rank_val.columns  = MONTHS
    pivot_rank_text.columns = MONTHS

    # Sort rows by average annual return descending
    row_order = pivot_rank_val.mean(axis=1).sort_values(ascending=False).index
    pivot_rank_val  = pivot_rank_val.reindex(row_order)
    pivot_rank_text = pivot_rank_text.reindex(row_order)

    # Build heatmap with rank + return as cell text
    z    = pivot_rank_val.values * 100
    flat = z[~np.isnan(z)]
    abs_max = max(abs(np.percentile(flat, 5)), abs(np.percentile(flat, 95)))               if len(flat) > 0 else 1
    abs_max = abs_max if abs_max > 0 else 1

    text_vals = []
    for i in range(len(pivot_rank_val.index)):
        row_texts = []
        for j in range(len(pivot_rank_val.columns)):
            ret_val  = pivot_rank_val.iloc[i, j]
            rank_val = pivot_rank_text.iloc[i, j]
            if pd.notna(ret_val) and pd.notna(rank_val):
                row_texts.append(f"#{int(rank_val)}<br>{ret_val*100:+.1f}%")
            else:
                row_texts.append("")
        text_vals.append(row_texts)

    fig_rank = go.Figure(go.Heatmap(
        z=z,
        x=MONTHS,
        y=pivot_rank_val.index.tolist(),
        text=text_vals,
        texttemplate="%{text}",
        textfont={"size": 9, "color": THEME["text_primary"]},
        colorscale=HEATMAP_COLORSCALE,
        zmin=-abs_max, zmax=abs_max, zmid=0,
        showscale=True,
        colorbar=dict(
            title=dict(text="Return (%)",
                       font=dict(size=10, color=THEME["text_secondary"])),
            tickfont=dict(color=THEME["text_secondary"], size=9),
            outlinewidth=0, bgcolor=THEME["bg"], thickness=12, len=0.8,
        ),
        xgap=2, ygap=1.5,
    ))
    fig_rank.update_layout(
        paper_bgcolor=THEME["bg"], plot_bgcolor=THEME["bg"],
        font=dict(family=THEME["font"], color=THEME["text_primary"], size=11),
        xaxis=dict(side="top", tickfont=dict(size=11, color=THEME["text_secondary"]),
                   showgrid=False),
        yaxis=dict(tickfont=dict(size=10, color=THEME["text_secondary"]),
                   showgrid=False, autorange="reversed"),
        margin=dict(l=10, r=80, t=40, b=20),
        height=max(300, len(pivot_rank_val) * 56 + 80),
    )
    st.plotly_chart(fig_rank, use_container_width=True)
    st.caption(
        f"#1 = best performing · #{len(pivot_rank_val)} = worst performing · "
        f"Values in % (price returns only) · {metric_label}"
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 2: BEST AND WORST MONTH PER ASSET CLASS ──────────────────────────
st.markdown('''<div class="section-header">Best and Worst Month by Asset Class</div>''',
            unsafe_allow_html=True)

summary_rows = []
for ac in ROTATION_CLASSES:
    ac_data = ac_monthly_avg[ac_monthly_avg["asset_class"] == ac]
    if ac_data.empty:
        continue
    best_row  = ac_data.loc[ac_data[metric_col].idxmax()]
    worst_row = ac_data.loc[ac_data[metric_col].idxmin()]
    summary_rows.append({
        "Asset Class":  ac,
        "Best Month":   MONTH_FULL[int(best_row["month"])],
        "Best Return":  f"{best_row[metric_col]*100:+.2f}%",
        "Worst Month":  MONTH_FULL[int(worst_row["month"])],
        "Worst Return": f"{worst_row[metric_col]*100:+.2f}%",
    })

if summary_rows:
    st.dataframe(
        pd.DataFrame(summary_rows),
        use_container_width=True, hide_index=True
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 3: SUB-CLASS ROTATION WITHIN ASSET CLASS ─────────────────────────
# For selected asset class, shows how sub-classes rotate across months
st.markdown('''<div class="section-header">Sub-Class Rotation within Asset Class</div>''',
            unsafe_allow_html=True)

col_ac_sel, _ = st.columns([1, 2])
with col_ac_sel:
    ac_for_rotation = st.selectbox(
        "Select asset class",
        options=ROTATION_CLASSES,
        index=0,
        key="rot_ac"
    )

subclass_stats = stats[stats["asset_class"] == ac_for_rotation].copy()

if not subclass_stats.empty:
    sc_monthly_avg = (
        subclass_stats
        .groupby(["sub_class", "month"])[metric_col]
        .mean()
        .reset_index()
    )

    pivot_sc = sc_monthly_avg.pivot(
        index="sub_class", columns="month", values=metric_col
    )
    pivot_sc = pivot_sc.reindex(columns=range(1, 13))
    pivot_sc.columns = MONTHS

    # Sort by average annual return descending
    pivot_sc = pivot_sc.reindex(
        pivot_sc.mean(axis=1).sort_values(ascending=False).index
    )

    fig_sc = build_heatmap(pivot_sc, value_col_label="Return (%)")
    st.plotly_chart(fig_sc, use_container_width=True)
    st.caption(
        f"{len(pivot_sc)} sub-classes within {ac_for_rotation} · "
        f"Sorted by average annual return · {metric_label} · "
        f"All values in % (price returns only)"
    )
else:
    st.info(f"No data available for {ac_for_rotation} under current filters.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 4: SEASONAL ROTATION CALENDAR ────────────────────────────────────
# Quick-reference card for each month showing best and worst asset class
st.markdown('''<div class="section-header">Seasonal Rotation Calendar</div>''',
            unsafe_allow_html=True)

st.markdown(
    f'''<div class="info-card">
    Each card shows the historically strongest and weakest investable asset
    class for that month based on {metric_label.lower()}.
    </div>''',
    unsafe_allow_html=True
)

if not ranking_df.empty:
    cal_cols = st.columns(6)
    for i, month_num in enumerate(range(1, 13)):
        with cal_cols[i % 6]:
            month_data = ranking_df[
                ranking_df["month"] == month_num
            ].sort_values(metric_col, ascending=False)

            if month_data.empty:
                continue

            best_ac   = month_data.iloc[0]["asset_class"]
            best_ret  = month_data.iloc[0][metric_col]
            worst_ac  = month_data.iloc[-1]["asset_class"]
            worst_ret = month_data.iloc[-1][metric_col]

            st.markdown(
                f'''<div style="background:{THEME["surface"]};
                border:1px solid {THEME["border"]};
                border-top:3px solid {THEME["primary"]};
                border-radius:8px;padding:0.75rem;
                margin-bottom:0.5rem;text-align:center;">
                <div style="font-weight:700;font-size:0.85rem;
                color:{THEME["text_primary"]};margin-bottom:0.4rem;">
                {MONTH_FULL[month_num][:3]}</div>
                <div style="font-size:0.75rem;color:{THEME["positive"]};
                font-weight:600;">▲ {best_ac}</div>
                <div style="font-size:0.72rem;color:{THEME["text_secondary"]};">
                {best_ret*100:+.1f}%</div>
                <div style="font-size:0.75rem;color:{THEME["negative"]};
                font-weight:600;margin-top:0.3rem;">▼ {worst_ac}</div>
                <div style="font-size:0.72rem;color:{THEME["text_secondary"]};">
                {worst_ret*100:+.1f}%</div>
                </div>''',
                unsafe_allow_html=True
            )

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown("""
**What is asset class rotation?**

Rotation is the tendency for different asset classes to outperform and
underperform in a cyclical pattern through the year. Capital flows toward
asset classes with seasonal tailwinds and away from those with headwinds.

**Why is Fixed Income shown as Bond ETF returns here?**

Bond yields (e.g. US 10Y Treasury Yield changes of +20 bps) are in
completely different units from equity returns (+2%). If both were
included in the same ranking, the tiny bps moves would always rank last
regardless of their economic significance. By using only Bond ETF price
returns (e.g. TLT, HYG, India Bond ETF), Fixed Income is expressed in
the same percentage terms as equities and commodities, making the
ranking meaningful.

**Why are Macro and Volatility excluded?**

GDP growth rates, CPI changes, and unemployment readings are economic
data, not investment returns. VIX levels are a fear gauge. Neither can
be directly invested in. Including them would produce rankings that
mix investment returns with economic statistics, which is meaningless.

**Sub-class rotation**

Within each asset class, sub-categories rotate too. For example within
Indian Equity, large caps may lead in one month while midcaps lead in
another. The sub-class rotation heatmap reveals these finer patterns.

**How to use the rotation calendar**

Before each month, check which asset class has historically been
strongest. This is a starting point for review — not a prediction.
Always combine seasonal signals with current macro context.
""")
