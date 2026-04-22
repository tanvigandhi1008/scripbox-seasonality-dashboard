
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 03_Regime_Analysis.py
# PURPOSE: Shows how seasonal patterns change under different macro regimes.
#
# REGIME CARD DESIGN:
#   Each card shows the classification label AND the underlying data point
#   that produced it, so every label is self-justifying.
#   Rupee Strength label removed — replaced with factual USD/INR data only.
#   Rate, Equity, Risk cards show the exact metric and threshold used.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st

from utils.data_loader import (
    load_metadata, filter_by_market_scope, render_sidebar,
    inject_css, prepare_stats, build_heatmap,
    load_monthly_returns, THEME, MONTHS, MONTH_FULL
)
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="Regime Analysis · Scripbox Seasonality",
    page_icon="🔀",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
render_sidebar()

scope          = st.session_state.get("market_scope", "Domestic")
currency       = st.session_state.get("currency", "local")
lookback       = st.session_state.get("lookback_years", 25)
heatmap_metric = st.session_state.get("heatmap_metric", "Average Return")
metric_col     = "avg_return" if heatmap_metric == "Average Return" else "median_return"

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
BASE      = "/content/drive/MyDrive/seasonality_dashboard"
PROCESSED = f"{BASE}/data/processed"

@st.cache_data(ttl=300)
def load_regime_labels():
    return pd.read_csv(f"{PROCESSED}/regime_labels.csv",
                       index_col=0, parse_dates=True)

@st.cache_data(ttl=300)
def load_monthly_returns_cached(curr):
    fname = "monthly_returns_inr.csv" if curr == "inr" else "monthly_returns.csv"
    return pd.read_csv(f"{PROCESSED}/{fname}", index_col=0, parse_dates=True)

stats, meta   = prepare_stats(currency, scope, lookback)
regimes       = load_regime_labels()
monthly_rets  = load_monthly_returns_cached(currency)

visible        = set(meta["name"].tolist())
available_cols = [c for c in monthly_rets.columns if c in visible]
monthly_rets   = monthly_rets[available_cols]

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Regime Analysis</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    How seasonal patterns change under different macro regimes ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"}
    </div>''',
    unsafe_allow_html=True
)

st.markdown(
    '''<div class="info-card">
    Seasonal averages across all years can be misleading — the same month
    can behave very differently depending on the macro environment.
    This page filters historical data to only months matching the selected
    regime, giving more relevant signals for the current environment.
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── CURRENT REGIME CARDS ──────────────────────────────────────────────────────
# Each card shows: classification label + exact underlying data point.
# This makes every label self-justifying — the user can see both
# what we concluded and what number drove that conclusion.
#
# Rupee Strength: no qualitative label shown. Only factual USD/INR data.
# Rate regime: based on US Fed Funds Rate monthly change
# Equity regime: based on Nifty 50 trailing 3-month return
# Risk regime: based on VIX end-of-month level

st.markdown('''<div class="section-header">Current Macro Regime</div>''',
            unsafe_allow_html=True)

latest_regime = regimes.dropna(how="all").iloc[-1]
latest_date   = regimes.dropna(how="all").index[-1]

# Load the raw monthly returns to get the underlying metric values
mr_local = load_monthly_returns_cached("local")

# Get the most recent Fed Funds Rate change
fed_val = None
if "US Federal Funds Rate" in mr_local.columns:
    fed_series = mr_local["US Federal Funds Rate"].dropna()
    if not fed_series.empty:
        fed_val = fed_series.iloc[-1]

# Get the most recent Nifty 50 trailing 3-month return
nifty_3m_val = None
if "Nifty 50" in mr_local.columns:
    nifty = mr_local["Nifty 50"].dropna()
    if len(nifty) >= 3:
        nifty_3m_val = (1 + nifty.iloc[-3:]).prod() - 1

# Get the most recent VIX level from raw file
vix_val = None
try:
    RAW = f"{BASE}/data/raw"
    vm_raw = pd.read_csv(f"{RAW}/volatility_macro.csv",
                         index_col=0, parse_dates=True)
    if "VIX US Equity Volatility" in vm_raw.columns:
        vix_series = vm_raw["VIX US Equity Volatility"].dropna()
        if not vix_series.empty:
            vix_val = vix_series.resample("ME").last().dropna().iloc[-1]
except Exception:
    pass

# Get the most recent USD/INR return and 12-month cumulative
usdinr_last_ret = None
usdinr_cum_12   = None
if "USD/INR" in mr_local.columns:
    usdinr = mr_local["USD/INR"].dropna()
    if not usdinr.empty:
        usdinr_last_ret = usdinr.iloc[-1] * 100
        last_12 = usdinr.iloc[-12:] if len(usdinr) >= 12 else usdinr
        usdinr_cum_12   = ((1 + last_12).prod() - 1) * 100

REGIME_COLORS = {
    "Rising":   "#E53935",
    "Falling":  "#43A047",
    "Neutral":  "#FB8C00",
    "Bull":     "#43A047",
    "Bear":     "#E53935",
    "Risk-Off": "#E53935",
    "Risk-On":  "#43A047",
    "Unknown":  "#9E9E9E",
}

regime_cols = st.columns(4)

# ── CARD 1: Rate Environment ──────────────────────────────────────────────────
rate_val = str(latest_regime.get("rate_regime", "Unknown"))
if pd.isna(rate_val) or rate_val == "nan": rate_val = "Unknown"
rate_color = REGIME_COLORS.get(rate_val, "#9E9E9E")
fed_note   = (
    f"Fed Funds Rate: {fed_val:+.2f}pp last month"
    if fed_val is not None else "Fed Funds Rate: no recent data"
)
threshold_note_rate = (
    "Rising if change > 0 · Falling if change < 0 · Neutral if unchanged"
)
regime_cols[0].markdown(
    f'''<div style="background:{THEME["surface"]};
    border:1px solid {THEME["border"]};
    border-top:4px solid {rate_color};
    border-radius:8px;padding:0.9rem;text-align:center;">
    <div style="font-size:0.75rem;font-weight:600;
    color:{THEME["text_secondary"]};margin-bottom:0.3rem;">
    Rate Environment</div>
    <div style="font-size:1.1rem;font-weight:700;color:{rate_color};">
    {rate_val}</div>
    <div style="font-size:0.7rem;color:{THEME["text_muted"]};
    margin-top:0.3rem;">{fed_note}</div>
    <div style="font-size:0.65rem;color:{THEME["text_muted"]};
    margin-top:0.2rem;font-style:italic;">{threshold_note_rate}</div>
    <div style="font-size:0.65rem;color:{THEME["text_muted"]};">
    as of {latest_date.strftime("%b %Y")}</div>
    </div>''',
    unsafe_allow_html=True
)

# ── CARD 2: USD/INR — factual only, no qualitative label ─────────────────────
if usdinr_last_ret is not None:
    usdinr_color = (
        THEME["negative"] if usdinr_last_ret >= 0
        else THEME["positive"]
    )
    regime_cols[1].markdown(
        f'''<div style="background:{THEME["surface"]};
        border:1px solid {THEME["border"]};
        border-top:4px solid {THEME["primary"]};
        border-radius:8px;padding:0.9rem;text-align:center;">
        <div style="font-size:0.75rem;font-weight:600;
        color:{THEME["text_secondary"]};margin-bottom:0.3rem;">
        USD/INR</div>
        <div style="font-size:0.95rem;font-weight:700;
        color:{THEME["text_primary"]};">
        Last month: {usdinr_last_ret:+.2f}%</div>
        <div style="font-size:0.95rem;font-weight:700;
        color:{THEME["text_primary"]};">
        Last 12M: {usdinr_cum_12:+.2f}%</div>
        <div style="font-size:0.65rem;color:{THEME["text_muted"]};
        margin-top:0.3rem;font-style:italic;">
        + = rupee weakened · − = rupee strengthened</div>
        <div style="font-size:0.65rem;color:{THEME["text_muted"]};">
        as of {latest_date.strftime("%b %Y")}</div>
        </div>''',
        unsafe_allow_html=True
    )
else:
    regime_cols[1].markdown(
        f'''<div style="background:{THEME["surface"]};
        border:1px solid {THEME["border"]};
        border-top:4px solid {THEME["primary"]};
        border-radius:8px;padding:0.9rem;text-align:center;">
        <div style="font-size:0.75rem;font-weight:600;
        color:{THEME["text_secondary"]};">USD/INR</div>
        <div style="font-size:0.85rem;color:{THEME["text_muted"]};">
        Not available</div>
        </div>''',
        unsafe_allow_html=True
    )

# ── CARD 3: Equity Trend ──────────────────────────────────────────────────────
eq_val = str(latest_regime.get("equity_regime", "Unknown"))
if pd.isna(eq_val) or eq_val == "nan": eq_val = "Unknown"
eq_color   = REGIME_COLORS.get(eq_val, "#9E9E9E")
nifty_note = (
    f"Nifty 50 trailing 3M: {nifty_3m_val*100:+.1f}%"
    if nifty_3m_val is not None else "Nifty 50 3M: no recent data"
)
threshold_note_eq = (
    "Bull if 3M > +5% · Bear if 3M < −5% · Neutral otherwise"
)
regime_cols[2].markdown(
    f'''<div style="background:{THEME["surface"]};
    border:1px solid {THEME["border"]};
    border-top:4px solid {eq_color};
    border-radius:8px;padding:0.9rem;text-align:center;">
    <div style="font-size:0.75rem;font-weight:600;
    color:{THEME["text_secondary"]};margin-bottom:0.3rem;">
    Equity Trend</div>
    <div style="font-size:1.1rem;font-weight:700;color:{eq_color};">
    {eq_val}</div>
    <div style="font-size:0.7rem;color:{THEME["text_muted"]};
    margin-top:0.3rem;">{nifty_note}</div>
    <div style="font-size:0.65rem;color:{THEME["text_muted"]};
    margin-top:0.2rem;font-style:italic;">{threshold_note_eq}</div>
    <div style="font-size:0.65rem;color:{THEME["text_muted"]};">
    as of {latest_date.strftime("%b %Y")}</div>
    </div>''',
    unsafe_allow_html=True
)

# ── CARD 4: Risk Appetite ─────────────────────────────────────────────────────
risk_val = str(latest_regime.get("risk_regime", "Unknown"))
if pd.isna(risk_val) or risk_val == "nan": risk_val = "Unknown"
risk_color = REGIME_COLORS.get(risk_val, "#9E9E9E")
vix_note   = (
    f"VIX level: {vix_val:.1f}"
    if vix_val is not None else "VIX: no recent data"
)
threshold_note_risk = (
    "Risk-Off if VIX > 25 · Risk-On if VIX < 15 · Neutral otherwise"
)
regime_cols[3].markdown(
    f'''<div style="background:{THEME["surface"]};
    border:1px solid {THEME["border"]};
    border-top:4px solid {risk_color};
    border-radius:8px;padding:0.9rem;text-align:center;">
    <div style="font-size:0.75rem;font-weight:600;
    color:{THEME["text_secondary"]};margin-bottom:0.3rem;">
    Risk Appetite</div>
    <div style="font-size:1.1rem;font-weight:700;color:{risk_color};">
    {risk_val}</div>
    <div style="font-size:0.7rem;color:{THEME["text_muted"]};
    margin-top:0.3rem;">{vix_note}</div>
    <div style="font-size:0.65rem;color:{THEME["text_muted"]};
    margin-top:0.2rem;font-style:italic;">{threshold_note_risk}</div>
    <div style="font-size:0.65rem;color:{THEME["text_muted"]};">
    as of {latest_date.strftime("%b %Y")}</div>
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── REGIME SELECTOR ───────────────────────────────────────────────────────────
st.markdown('''<div class="section-header">Select Regime to Analyse</div>''',
            unsafe_allow_html=True)

REGIME_LABELS = {
    "rate_regime":   "Rate Environment",
    "rupee_regime":  "Rupee (USD/INR)",
    "equity_regime": "Equity Trend",
    "risk_regime":   "Risk Appetite",
}

col_type, col_val, col_series_ac = st.columns([1, 1, 1])

with col_type:
    regime_type = st.selectbox(
        "Regime Dimension",
        options=list(REGIME_LABELS.keys()),
        format_func=lambda x: REGIME_LABELS[x],
        key="regime_type"
    )

available_vals = sorted(regimes[regime_type].dropna().unique().tolist())

with col_val:
    regime_val = st.selectbox(
        "Regime Value",
        options=available_vals,
        key="regime_val"
    )

with col_series_ac:
    ac_options  = ["All"] + sorted(meta["asset_class"].unique().tolist())
    selected_ac = st.selectbox("Asset Class", ac_options, key="regime_ac")

# ── FILTER MONTHS BY REGIME ───────────────────────────────────────────────────
regime_months   = pd.to_datetime(
    regimes[regimes[regime_type] == regime_val].index
)
mr_regime       = monthly_rets[monthly_rets.index.isin(regime_months)].copy()
n_regime_months = len(mr_regime)
total_months    = len(monthly_rets.dropna(how="all"))

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f'''<div class="info-card">
    <strong>{regime_val}</strong> regime:
    <strong>{n_regime_months} months</strong> out of {total_months} total
    ({n_regime_months/total_months*100:.0f}% of history).
    Stats below computed only from these {n_regime_months} months.
    Patterns with fewer than 5 observations per month are hidden.
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

if mr_regime.empty:
    st.warning("No months found for this regime. Try a different selection.")
    st.stop()

# ── REGIME HEATMAP ────────────────────────────────────────────────────────────
st.markdown(
    f'''<div class="section-header">
    Seasonality Heatmap — {regime_val} Regime</div>''',
    unsafe_allow_html=True
)

MIN_OBS_REGIME = 5

def compute_regime_stats(mr_df, series_list, metric):
    rows = []
    for col in series_list:
        if col not in mr_df.columns:
            continue
        s = mr_df[col].dropna()
        for month_num in range(1, 13):
            clean = s[s.index.month == month_num].dropna()
            n_obs = len(clean)
            if n_obs < MIN_OBS_REGIME:
                continue
            val = clean.mean() if metric == "avg_return" else clean.median()
            rows.append({
                "name":     col,
                "month":    month_num,
                metric:     val,
                "n_obs":    n_obs,
                "win_rate": (clean > 0).mean(),
            })
    return pd.DataFrame(rows)

if selected_ac != "All":
    ac_series     = meta[meta["asset_class"] == selected_ac]["name"].tolist()
    series_to_use = [s for s in available_cols if s in ac_series]
else:
    series_to_use = available_cols

# Exclude yield/spread series — bps vs % comparability issue
meta_lookup  = meta.set_index("name").to_dict("index")
price_series = [
    s for s in series_to_use
    if meta_lookup.get(s, {}).get("series_type", "price")
    not in {"yield", "spread", "rate", "index"}
    and meta_lookup.get(s, {}).get("asset_class", "")
    not in {"Macro", "Volatility"}
]

regime_stats = compute_regime_stats(mr_regime, price_series, metric_col)

if regime_stats.empty:
    st.info(
        "Insufficient data for this regime and asset class combination. "
        "Try a different selection."
    )
else:
    pivot = regime_stats.pivot_table(
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

    fig = build_heatmap(
        pivot, value_col_label="Return (%)", is_basis_points=False
    )
    st.plotly_chart(
        fig, use_container_width=True, key="regime_heatmap"
    )
    st.caption(
        f"{len(pivot)} series · {regime_val} regime · "
        f"{n_regime_months} months · {heatmap_metric} · "
        f"Min {MIN_OBS_REGIME} observations per cell"
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ── REGIME vs UNCONDITIONAL COMPARISON ────────────────────────────────────────
st.markdown(
    f'''<div class="section-header">
    Regime vs Unconditional — Does the Regime Change the Pattern?
    </div>''',
    unsafe_allow_html=True
)

default_s  = "Nifty 50" if "Nifty 50" in price_series else (
    price_series[0] if price_series else None
)
if default_s:
    compare_series = st.selectbox(
        "Select series for comparison",
        options=sorted(price_series),
        index=sorted(price_series).index(default_s)
              if default_s in price_series else 0,
        key="regime_compare_series"
    )

    series_all    = (
        monthly_rets[compare_series].dropna()
        if compare_series in monthly_rets.columns else pd.Series()
    )
    series_regime = (
        mr_regime[compare_series].dropna()
        if compare_series in mr_regime.columns else pd.Series()
    )

    unconditional_monthly = []
    regime_monthly        = []

    for month_num in range(1, 13):
        all_vals    = series_all[series_all.index.month == month_num].dropna()
        regime_vals = series_regime[series_regime.index.month == month_num].dropna()
        unconditional_monthly.append(
            all_vals.mean() if len(all_vals) >= 3 else np.nan
        )
        regime_monthly.append(
            regime_vals.mean() if len(regime_vals) >= MIN_OBS_REGIME else np.nan
        )

    fig_compare = go.Figure()
    fig_compare.add_trace(go.Bar(
        x=MONTHS,
        y=[v * 100 if pd.notna(v) else None for v in unconditional_monthly],
        name="Unconditional (all years)",
        marker_color=THEME["text_secondary"],
        opacity=0.5,
    ))
    fig_compare.add_trace(go.Scatter(
        x=MONTHS,
        y=[v * 100 if pd.notna(v) else None for v in regime_monthly],
        name=f"{regime_val} regime only",
        mode="lines+markers",
        line=dict(color=THEME["primary"], width=2.5),
        marker=dict(size=8, color=THEME["primary"]),
    ))
    fig_compare.update_layout(
        paper_bgcolor=THEME["bg"], plot_bgcolor=THEME["bg"],
        font=dict(family=THEME["font"], color=THEME["text_primary"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=11)),
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(
            showgrid=True, gridcolor=THEME["border"],
            ticksuffix="%", zeroline=True,
            zerolinecolor=THEME["border"], zerolinewidth=1.5
        ),
        margin=dict(l=20, r=20, t=40, b=20),
        height=380,
        barmode="overlay",
    )
    st.plotly_chart(
        fig_compare, use_container_width=True,
        key="regime_comparison_chart"
    )
    st.caption(
        f"{compare_series} · Grey bars = all-history average · "
        f"Orange line = {regime_val} regime only"
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ── REGIME HISTORY TIMELINE ───────────────────────────────────────────────────
st.markdown('''<div class="section-header">Regime History</div>''',
            unsafe_allow_html=True)

regime_history = regimes[[regime_type]].copy()
regime_history["is_selected"] = (
    regime_history[regime_type] == regime_val
).astype(int)
regime_history = regime_history.dropna()

REGIME_COLORS_ALL = {
    "Rising":   "#E53935", "Falling":  "#43A047", "Neutral":  "#FB8C00",
    "Weak Rupee": "#E53935", "Strong Rupee": "#43A047",
    "Stable Rupee": "#FB8C00",
    "Bull":     "#43A047", "Bear":     "#E53935",
    "Risk-Off": "#E53935", "Risk-On":  "#43A047", "Unknown":  "#9E9E9E",
}

fig_hist = go.Figure()
fig_hist.add_trace(go.Bar(
    x=regime_history.index,
    y=regime_history["is_selected"],
    marker_color=[
        REGIME_COLORS_ALL.get(regime_val, THEME["primary"])
        if v == 1 else THEME["border"]
        for v in regime_history["is_selected"]
    ],
    showlegend=False,
))
fig_hist.update_layout(
    paper_bgcolor=THEME["bg"], plot_bgcolor=THEME["bg"],
    font=dict(family=THEME["font"], color=THEME["text_primary"]),
    xaxis=dict(showgrid=False, tickfont=dict(size=9)),
    yaxis=dict(showgrid=False, visible=False),
    margin=dict(l=10, r=10, t=10, b=30),
    height=120,
)
st.plotly_chart(
    fig_hist, use_container_width=True, key="regime_history_timeline"
)
st.caption(
    f"Highlighted = months classified as {regime_val} · "
    f"{n_regime_months} months total · "
    f"{regime_history.index[0].strftime('%Y')} to "
    f"{regime_history.index[-1].strftime('%Y')}"
)

# ── DISCLAIMER ────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f'''<p style="font-size:0.78rem;color:{THEME["text_muted"]};
    font-style:italic;">
    Regime classification methodology: Rate regime from US Fed Funds Rate
    monthly change (Rising/Falling/Neutral). Rupee regime from USD/INR
    monthly return (Weak > +0.5%, Strong < −0.5%, Stable otherwise).
    Equity regime from Nifty 50 trailing 3-month return (Bull > +5%,
    Bear < −5%, Neutral otherwise). Risk regime from VIX end-of-month
    level (Risk-Off > 25, Risk-On < 15, Neutral otherwise).
    Fewer observations = higher uncertainty — interpret with caution
    when regime n < 10 per month.
    </p>''',
    unsafe_allow_html=True
)
