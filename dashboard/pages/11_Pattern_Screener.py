
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 11_Pattern_Screener.py
# PURPOSE: Screening tool to find the strongest and most consistent seasonal
#          patterns across all investable series in the current scope.
#
# FILTERING RULES:
#   - filter_for_multiasset applied: removes yield/spread/rate/index series
#     and Macro/Volatility classes. All scored patterns are price returns in
#     comparable % terms. Consistency scores are therefore comparable.
#   - Benchmark series hidden by default via toggle — only investable series
#     shown unless user explicitly enables benchmarks.
#   - Optional regime filter: recomputes scores from regime months only.
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
from scipy import stats as scipy_stats

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pattern Screener · Scripbox Seasonality",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
render_sidebar()

# ── READ CONTROLS ─────────────────────────────────────────────────────────────
scope          = st.session_state.get("market_scope", "Domestic")
currency       = st.session_state.get("currency", "local")
lookback       = st.session_state.get("lookback_years", 25)
heatmap_metric = st.session_state.get("heatmap_metric", "Average Return")

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
# Note: global sig_filter not applied here — the screener has its own
# granular p-value filter so applying both would double-filter confusingly
stats_all, meta = prepare_stats(currency, scope, lookback)

# Apply multi-asset filter: removes yield/spread/rate/index and Macro/Volatility
# All remaining series are price-return series so scores are comparable
stats = filter_for_multiasset(stats_all)

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Pattern Screener</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Screen for the strongest and most consistent seasonal patterns ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"} ·
    {metric_label}
    </div>''',
    unsafe_allow_html=True
)

st.markdown(
    '''<div class="info-card">
    The <strong>Consistency Score</strong> combines win rate (40%), return
    magnitude (40%), and statistical significance (20%) into a single 0–1 score.
    Score above 0.65 = strong, repeatable pattern worth investigating.
    All series shown are price-return series in % terms — yield and macro
    series excluded so scores are directly comparable across asset classes.
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── OPTIONAL REGIME FILTER ────────────────────────────────────────────────────
# If user selects a regime, stats are recomputed from regime months only.
# This surfaces patterns that are strong specifically in the current environment.

BASE_PS      = "/content/drive/MyDrive/seasonality_dashboard"
PROCESSED_PS = f"{BASE_PS}/data/processed"

@st.cache_data(ttl=300)
def load_regime_ps():
    return pd.read_csv(f"{PROCESSED_PS}/regime_labels.csv",
                       index_col=0, parse_dates=True)

@st.cache_data(ttl=300)
def load_mr_ps(curr):
    fname = "monthly_returns_inr.csv" if curr == "inr" else "monthly_returns.csv"
    return pd.read_csv(f"{PROCESSED_PS}/{fname}", index_col=0, parse_dates=True)

regimes_ps     = load_regime_ps()
latest_regime  = regimes_ps.dropna(how="all").iloc[-1]
current_equity = str(latest_regime.get("equity_regime", "Unknown"))
current_rate   = str(latest_regime.get("rate_regime",   "Unknown"))

REGIME_OPTIONS = {
    "None (use full history)": None,
    "Rate: Falling":           ("rate_regime",   "Falling"),
    "Rate: Rising":            ("rate_regime",   "Rising"),
    "Rate: Neutral":           ("rate_regime",   "Neutral"),
    "Equity: Bull":            ("equity_regime", "Bull"),
    "Equity: Bear":            ("equity_regime", "Bear"),
    "Equity: Neutral":         ("equity_regime", "Neutral"),
    "Risk: Risk-Off":          ("risk_regime",   "Risk-Off"),
    "Risk: Risk-On":           ("risk_regime",   "Risk-On"),
}

selected_regime_label = st.selectbox(
    "Regime Filter (optional — recomputes scores from matching months only)",
    options=list(REGIME_OPTIONS.keys()),
    index=0,
    key="screener_regime",
    help=(
        f"Current regime: Equity = {current_equity}, Rates = {current_rate}. "
        "Select a regime to see only patterns from months matching that environment."
    )
)

regime_filter = REGIME_OPTIONS[selected_regime_label]

# If regime filter is active, recompute stats from regime months only
if regime_filter is not None:
    regime_col_ps, regime_val_ps = regime_filter
    regime_months_ps = regimes_ps[
        regimes_ps[regime_col_ps] == regime_val_ps
    ].index

    mr_ps        = load_mr_ps(currency)
    mr_regime_ps = mr_ps[mr_ps.index.isin(regime_months_ps)]
    n_regime_ps  = len(mr_regime_ps)

    visible_ps   = set(meta["name"].tolist())
    # Only use price-return series for regime stats
    meta_lookup_ps = meta.set_index("name").to_dict("index")
    price_cols_ps  = [
        c for c in mr_regime_ps.columns
        if c in visible_ps and
        meta_lookup_ps.get(c, {}).get("series_type", "price")
        not in {"yield", "spread", "rate", "index"} and
        meta_lookup_ps.get(c, {}).get("asset_class", "")
        not in {"Macro", "Volatility"}
    ]

    MONTH_NAMES_PS = {1:"January",2:"February",3:"March",4:"April",
                      5:"May",6:"June",7:"July",8:"August",
                      9:"September",10:"October",11:"November",12:"December"}

    regime_rows = []
    for col in price_cols_ps:
        series_ps = mr_regime_ps[col].dropna()
        m_info    = meta_lookup_ps.get(col, {})
        for month_num in range(1, 13):
            clean = series_ps[series_ps.index.month == month_num].dropna()
            n_obs = len(clean)
            if n_obs < 3:
                continue
            row_ps = {
                "name":          col,
                "month":         month_num,
                "month_name":    MONTH_NAMES_PS[month_num],
                "n_obs":         n_obs,
                "avg_return":    float(clean.mean()),
                "median_return": float(clean.median()),
                "win_rate":      float((clean > 0).mean()),
                "asset_class":   m_info.get("asset_class", ""),
                "sub_class":     m_info.get("sub_class", ""),
                "series_type":   m_info.get("series_type", ""),
                "investability": m_info.get("investability", ""),
                "t_stat":        np.nan,
                "p_value":       np.nan,
            }
            t, p = scipy_stats.ttest_1samp(clean, popmean=0)
            row_ps["t_stat"]  = round(float(t), 4)
            row_ps["p_value"] = round(float(p), 4)
            regime_rows.append(row_ps)

    if regime_rows:
        stats = pd.DataFrame(regime_rows)
        st.info(
            f"Regime filter active: **{selected_regime_label}** — "
            f"showing patterns from **{n_regime_ps} months** only "
            f"({n_regime_ps/315*100:.0f}% of full history). "
            f"Consistency scores recomputed for this regime."
        )
    else:
        st.warning("No data for this regime. Showing full history.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── COMPUTE CONSISTENCY SCORE ─────────────────────────────────────────────────
# Consistency Score = 40% win rate + 40% normalised magnitude + 20% significance
# Score 0 to 1. Above 0.65 = strong reliable pattern.
abs_returns = stats[metric_col].abs()
max_abs     = abs_returns.quantile(0.95)
if max_abs == 0:
    max_abs = 1

stats = stats.copy()
stats["norm_magnitude"]    = (stats[metric_col].abs() / max_abs).clip(0, 1)
stats["consistency_score"] = (
    stats["win_rate"].fillna(0) * 0.4 +
    stats["norm_magnitude"] * 0.4 +
    (1 - stats["p_value"].fillna(1).clip(0, 1)) * 0.2
).round(3)

# ── SCREENER FILTERS ──────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Screener Filters</div>''',
            unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    ac_options  = ["All"] + sorted(stats["asset_class"].unique().tolist())
    selected_ac = st.selectbox("Asset Class", ac_options, key="screen_ac")

with col2:
    month_options       = ["All months"] + list(MONTH_FULL.values())
    selected_month_name = st.selectbox("Month", month_options, key="screen_month")

with col3:
    direction = st.selectbox(
        "Direction",
        ["All", "Positive only", "Negative only"],
        key="screen_dir"
    )

with col4:
    min_win_rate = st.slider(
        "Min Win Rate (%)", min_value=0, max_value=90,
        value=50, step=5, key="screen_winrate"
    )

with col5:
    pval_threshold = st.selectbox(
        "p-value threshold",
        ["No filter", "p < 0.20", "p < 0.10", "p < 0.05"],
        key="screen_pval"
    )

min_score = st.slider(
    "Minimum Consistency Score (0 = show all, 0.65 = strong patterns only)",
    min_value=0.0, max_value=0.95, value=0.0, step=0.05,
    key="screen_score"
)

# Benchmark toggle — hidden by default since benchmarks are not investable
show_benchmarks = st.checkbox(
    "Include benchmark / reference series (S&P 500, Nikkei etc.)",
    value=False,
    key="screen_benchmarks",
    help="Benchmarks are reference indices, not directly investable. "
         "Untick to show only investable series."
)

# ── APPLY FILTERS ─────────────────────────────────────────────────────────────
screened = stats.copy()

# Merge investability if not present (regime recompute path may not have it)
if "investability" not in screened.columns:
    inv_map = dict(zip(meta["name"], meta["investability"]))
    screened["investability"] = screened["name"].map(inv_map)

if not show_benchmarks:
    screened = screened[screened["investability"] != "benchmark"]

if selected_ac != "All":
    screened = screened[screened["asset_class"] == selected_ac]

if selected_month_name != "All months":
    month_num = [k for k, v in MONTH_FULL.items() if v == selected_month_name][0]
    screened  = screened[screened["month"] == month_num]

if direction == "Positive only":
    screened = screened[screened[metric_col] > 0]
elif direction == "Negative only":
    screened = screened[screened[metric_col] < 0]

screened = screened[screened["win_rate"] >= min_win_rate / 100]

if pval_threshold == "p < 0.20":
    screened = screened[screened["p_value"] < 0.20]
elif pval_threshold == "p < 0.10":
    screened = screened[screened["p_value"] < 0.10]
elif pval_threshold == "p < 0.05":
    screened = screened[screened["p_value"] < 0.05]

screened = screened[screened["consistency_score"] >= min_score]

# ── RESULTS SUMMARY ───────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col_a, col_b, col_c = st.columns(3)
col_a.metric("Patterns Found", len(screened))
col_b.metric("Unique Series",  screened["name"].nunique())
col_c.metric(
    "Avg Consistency Score",
    f"{screened['consistency_score'].mean():.3f}" if not screened.empty else "—"
)

st.markdown("<hr>", unsafe_allow_html=True)

if screened.empty:
    st.info("No patterns match the current filters. Try relaxing them.")
    st.stop()

# ── RESULTS TABLE ─────────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Screener Results</div>''',
            unsafe_allow_html=True)

display_cols = [
    "name", "asset_class", "month_name", metric_col,
    "win_rate", "n_obs", "p_value", "consistency_score"
]
results_df = screened[display_cols].copy()
results_df.columns = [
    "Series", "Asset Class", "Month", metric_label,
    "Win Rate", "Observations", "p-value", "Consistency Score"
]

results_df[metric_label]        = results_df[metric_label].map(lambda x: f"{x*100:+.2f}%")
results_df["Win Rate"]          = results_df["Win Rate"].map(lambda x: f"{x*100:.0f}%")
results_df["p-value"]           = results_df["p-value"].map(lambda x: f"{x:.3f}")
results_df["Observations"]      = results_df["Observations"].map(
    lambda x: str(int(x)) if pd.notna(x) else ""
)
results_df["Consistency Score"] = results_df["Consistency Score"].map(
    lambda x: f"{x:.3f}"
)
results_df = results_df.sort_values("Consistency Score", ascending=False)

st.dataframe(results_df, use_container_width=True, hide_index=True)
st.caption(
    f"{len(results_df)} patterns · sorted by Consistency Score (highest first) · "
    f"{metric_label} · all values in % (price returns only)"
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── TOP PATTERNS HEATMAP ──────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Top Patterns — Heatmap View</div>''',
            unsafe_allow_html=True)

# Top 20 unique series by average consistency score across all months
top_series = (
    screened.groupby("name")["consistency_score"]
    .mean()
    .sort_values(ascending=False)
    .head(20)
    .index.tolist()
)

top_stats = stats[stats["name"].isin(top_series)].copy()

if not top_stats.empty:
    pivot_top = top_stats.pivot_table(
        index="name", columns="month",
        values=metric_col, aggfunc="mean"
    )
    pivot_top = pivot_top.reindex(columns=range(1, 13))
    pivot_top.columns = MONTHS

    # Sort rows by score descending
    score_order = (
        screened[screened["name"].isin(top_series)]
        .groupby("name")["consistency_score"]
        .mean()
        .sort_values(ascending=False)
    )
    pivot_top = pivot_top.reindex(
        [n for n in score_order.index if n in pivot_top.index]
    )

    # Label benchmark series
    inv_map = dict(zip(meta["name"], meta["investability"]))
    pivot_top.index = [
        f"{n} [Ref]" if inv_map.get(n) == "benchmark" else n
        for n in pivot_top.index
    ]

    # All series here are price returns — build_heatmap multiplies by 100
    # No basis point conversion needed
    fig = build_heatmap(pivot_top, value_col_label="Return (%)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"Top {len(pivot_top)} series by Consistency Score · "
        f"[Ref] = reference benchmark · {metric_label} · "
        f"All values in % (price returns only)"
    )

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown("""
**What is the Consistency Score?**

The Consistency Score is a single number from 0 to 1 that combines three
measures of how reliable a seasonal pattern is:

- **40% Win Rate** — how often the pattern repeated across years.
  A win rate of 70% means the asset went up in 70% of all Januaries
  in the dataset.
- **40% Return Magnitude** — how large the historical return is,
  normalised relative to the strongest patterns in the dataset.
- **20% Statistical Significance** — how unlikely the pattern is to
  be random noise (1 minus p-value). A p-value of 0.05 means only
  5% probability the pattern is random.

A score above 0.65 indicates a strong, repeatable, statistically
supported pattern. Below 0.40 means the pattern is weak or inconsistent.

**Why are yield and macro series excluded?**

Yield series (bond yields, credit spreads) move in basis points.
Macro series (GDP, CPI) are economic readings not investment returns.
Including them would produce Consistency Scores that are not comparable
to equity or commodity scores. All series shown here are price-return
series in percentage terms.

**How to use the screener practically**

A useful workflow before each month:
1. Set Month to the upcoming month
2. Set Direction to Positive only
3. Set Min Win Rate to 60%
4. Set p-value to p < 0.10
5. Sort by Consistency Score

This gives a shortlist of historically strong seasonal candidates
with statistical backing for the upcoming month.

**Regime filter**

When a regime filter is active, scores are recomputed using only months
from that regime. This surfaces patterns that are strong specifically
in the current macro environment rather than across all history.
Fewer months = less statistical certainty, so interpret with caution
when Regime n is below 10.

**Important caveat**

Consistency Score measures historical reliability only. It is not a
prediction. Past seasonal patterns can and do break down, especially
during structural shifts in monetary policy, market microstructure,
or global capital flows.
""")
