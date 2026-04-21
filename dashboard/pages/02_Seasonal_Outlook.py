
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 02_Seasonal_Outlook.py
# PURPOSE: Forward-looking seasonal signals for the current month and next
#          two months. Shows strongest historical patterns with confidence
#          indicators, and how current macro regime affects those patterns.
#
# REGIME CARDS: Rate Environment, Equity Trend, Risk Appetite are shown.
#   Rupee Strength card has been removed — rupee regime is computed from
#   rolling data and can flip day to day, which is misleading. Instead we
#   show the current USD/INR rate as a factual reference with no label.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st

from utils.data_loader import (
    load_metadata, load_seasonality_stats, load_monthly_returns,
    filter_by_market_scope, render_sidebar, inject_css,
    prepare_stats, filter_for_multiasset, THEME, MONTHS, MONTH_FULL
)
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Seasonal Outlook · Scripbox Seasonality",
    page_icon="🔭",
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
metric_col     = "avg_return" if heatmap_metric == "Average Return" else "median_return"

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
stats_all, meta = prepare_stats(currency, scope, lookback)

# Apply multi-asset filter: removes yield/spread/rate/index series and
# Macro/Volatility classes. This ensures all ranked patterns are from
# investable price-return series only, so scores are comparable.
stats_clean = filter_for_multiasset(stats_all)

# ── COMPUTE CONSISTENCY SCORE ─────────────────────────────────────────────────
# Consistency Score = weighted combination of three reliability factors:
#   40% Win Rate      — how often the pattern repeats across years
#   40% Return Size   — how large the historical return is (normalised)
#   20% Statistical   — how unlikely the pattern is to be random (1 - p_value)
# Score ranges 0 to 1. Above 0.65 = historically strong and reliable pattern.
abs_returns = stats_clean[metric_col].abs()
max_abs     = abs_returns.quantile(0.95)
if max_abs == 0:
    max_abs = 1
stats_clean = stats_clean.copy()
stats_clean["norm_magnitude"]    = (stats_clean[metric_col].abs() / max_abs).clip(0, 1)
stats_clean["consistency_score"] = (
    stats_clean["win_rate"].fillna(0) * 0.4 +
    stats_clean["norm_magnitude"] * 0.4 +
    (1 - stats_clean["p_value"].fillna(1).clip(0, 1)) * 0.2
).round(3)

# ── CURRENT DATE AND OUTLOOK MONTHS ──────────────────────────────────────────
today          = datetime.today()
current_month  = today.month
current_year   = today.year
# Show current month and next two months
outlook_months = [(current_month + i - 1) % 12 + 1 for i in range(3)]
outlook_labels = [MONTH_FULL[m] for m in outlook_months]

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Seasonal Outlook</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Forward-looking seasonal signals for {" · ".join(outlook_labels)} ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"}
    </div>''',
    unsafe_allow_html=True
)

st.markdown(
    f'''<div class="info-card">
    Strongest historical seasonal patterns for the
    <strong>current and next two months</strong> based on {lookback} years
    of data. Consistency Score ≥ 0.65 = historically reliable pattern.
    Use alongside fundamental and macro analysis — not as a standalone
    prediction. Yield, spread, macro and volatility series are excluded
    from rankings so all scores are comparable.
    </div>''',
    unsafe_allow_html=True
)

# ── CURRENT MACRO REGIME CONTEXT ─────────────────────────────────────────────
# Shows the three stable regime dimensions as factual context cards.
# Rate regime, equity regime, and risk regime are computed from monthly
# rolling data and are reasonably stable month to month.
#
# Rupee strength is NOT shown as a regime label because it is computed
# from short-term rolling data and can change day to day, which would
# introduce a misleading directional bias. Instead we show the current
# USD/INR rate as a factual reference.

from utils.data_loader import PROCESSED as PROCESSED_SO

@st.cache_data(ttl=300)
def load_regime_so():
    return pd.read_csv(f"{PROCESSED_SO}/regime_labels.csv",
                       index_col=0, parse_dates=True)

@st.cache_data(ttl=300)
def load_mr_so(curr):
    fname = "monthly_returns_inr.csv" if curr == "inr" else "monthly_returns.csv"
    return pd.read_csv(f"{PROCESSED_SO}/{fname}", index_col=0, parse_dates=True)

regimes_so     = load_regime_so()
latest_so      = regimes_so.dropna(how="all").iloc[-1]
latest_date_so = regimes_so.dropna(how="all").index[-1]

REGIME_COLORS = {
    "Rising":   "#E53935",  # red — rising rates are a headwind for bonds/equities
    "Falling":  "#43A047",  # green — falling rates are generally supportive
    "Neutral":  "#FB8C00",  # amber — no clear directional trend
    "Bull":     "#43A047",
    "Bear":     "#E53935",
    "Risk-Off": "#E53935",
    "Risk-On":  "#43A047",
    "Unknown":  "#9E9E9E",
}

st.markdown('''<div class="section-header">Current Macro Regime</div>''',
            unsafe_allow_html=True)

# Three regime cards + one USD/INR factual card
regime_col1, regime_col2, regime_col3, regime_col4 = st.columns(4)

# Rate environment card
rate_val = str(latest_so.get("rate_regime", "Unknown"))
if pd.isna(rate_val) or rate_val == "nan": rate_val = "Unknown"
rate_color = REGIME_COLORS.get(rate_val, "#9E9E9E")
regime_col1.markdown(
    f'''<div style="background:{THEME["surface"]};
    border:1px solid {THEME["border"]};
    border-top:4px solid {rate_color};
    border-radius:8px;padding:0.8rem;text-align:center;">
    <div style="font-size:0.75rem;font-weight:600;
    color:{THEME["text_secondary"]};margin-bottom:0.3rem;">Rate Environment</div>
    <div style="font-size:1.1rem;font-weight:700;color:{rate_color};">{rate_val}</div>
    <div style="font-size:0.68rem;color:{THEME["text_muted"]};margin-top:0.2rem;">
    as of {latest_date_so.strftime("%b %Y")}</div>
    </div>''',
    unsafe_allow_html=True
)

# Equity trend card
eq_val = str(latest_so.get("equity_regime", "Unknown"))
if pd.isna(eq_val) or eq_val == "nan": eq_val = "Unknown"
eq_color = REGIME_COLORS.get(eq_val, "#9E9E9E")
regime_col2.markdown(
    f'''<div style="background:{THEME["surface"]};
    border:1px solid {THEME["border"]};
    border-top:4px solid {eq_color};
    border-radius:8px;padding:0.8rem;text-align:center;">
    <div style="font-size:0.75rem;font-weight:600;
    color:{THEME["text_secondary"]};margin-bottom:0.3rem;">Equity Trend</div>
    <div style="font-size:1.1rem;font-weight:700;color:{eq_color};">{eq_val}</div>
    <div style="font-size:0.68rem;color:{THEME["text_muted"]};margin-top:0.2rem;">
    as of {latest_date_so.strftime("%b %Y")}</div>
    </div>''',
    unsafe_allow_html=True
)

# Risk appetite card
risk_val = str(latest_so.get("risk_regime", "Unknown"))
if pd.isna(risk_val) or risk_val == "nan": risk_val = "Unknown"
risk_color = REGIME_COLORS.get(risk_val, "#9E9E9E")
regime_col3.markdown(
    f'''<div style="background:{THEME["surface"]};
    border:1px solid {THEME["border"]};
    border-top:4px solid {risk_color};
    border-radius:8px;padding:0.8rem;text-align:center;">
    <div style="font-size:0.75rem;font-weight:600;
    color:{THEME["text_secondary"]};margin-bottom:0.3rem;">Risk Appetite</div>
    <div style="font-size:1.1rem;font-weight:700;color:{risk_color};">{risk_val}</div>
    <div style="font-size:0.68rem;color:{THEME["text_muted"]};margin-top:0.2rem;">
    as of {latest_date_so.strftime("%b %Y")}</div>
    </div>''',
    unsafe_allow_html=True
)

# USD/INR factual card — no label, just the rate and recent change
# We load the last two available monthly returns for USD/INR to compute
# the 1-month change. No qualitative interpretation is applied.
try:
    mr_for_fx = load_mr_so("local")
    if "USD/INR" in mr_for_fx.columns:
        usdinr_series = mr_for_fx["USD/INR"].dropna()
        # Most recent monthly return (decimal) converted to percent
        last_ret  = usdinr_series.iloc[-1] * 100
        last_date = usdinr_series.index[-1]
        # 12-month cumulative change: product of (1 + monthly_return) - 1
        last_12   = usdinr_series.iloc[-12:] if len(usdinr_series) >= 12 else usdinr_series
        cum_12    = ((1 + last_12).prod() - 1) * 100
        change_color = THEME["negative"] if last_ret >= 0 else THEME["positive"]
        regime_col4.markdown(
            f'''<div style="background:{THEME["surface"]};
            border:1px solid {THEME["border"]};
            border-top:4px solid {THEME["primary"]};
            border-radius:8px;padding:0.8rem;text-align:center;">
            <div style="font-size:0.75rem;font-weight:600;
            color:{THEME["text_secondary"]};margin-bottom:0.3rem;">USD/INR</div>
            <div style="font-size:0.85rem;font-weight:700;
            color:{THEME["text_primary"]};">
            Last month: {last_ret:+.2f}%</div>
            <div style="font-size:0.85rem;font-weight:700;
            color:{THEME["text_primary"]};">
            Last 12M: {cum_12:+.2f}%</div>
            <div style="font-size:0.68rem;color:{THEME["text_muted"]};margin-top:0.2rem;">
            + = rupee weakened · as of {last_date.strftime("%b %Y")}</div>
            </div>''',
            unsafe_allow_html=True
        )
    else:
        regime_col4.markdown(
            f'''<div style="background:{THEME["surface"]};
            border:1px solid {THEME["border"]};
            border-top:4px solid {THEME["primary"]};
            border-radius:8px;padding:0.8rem;text-align:center;">
            <div style="font-size:0.75rem;font-weight:600;
            color:{THEME["text_secondary"]};">USD/INR</div>
            <div style="font-size:0.85rem;color:{THEME["text_muted"]};">
            Not available</div>
            </div>''',
            unsafe_allow_html=True
        )
except Exception:
    pass

# ── REGIME IMPACT EXPANDER ────────────────────────────────────────────────────
# Shows how current equity and rate regime changes the top patterns for the
# current month vs the unconditional (all-history) average.
equity_val = str(latest_so.get("equity_regime", "Unknown"))
rate_val_r = str(latest_so.get("rate_regime", "Unknown"))
if pd.isna(equity_val) or equity_val == "nan": equity_val = "Unknown"
if pd.isna(rate_val_r) or rate_val_r == "nan": rate_val_r = "Unknown"

if equity_val not in ["Unknown"] or rate_val_r not in ["Unknown"]:
    with st.expander(
        f"How does the current regime ({equity_val} equity · "
        f"{rate_val_r} rates) change {MONTH_FULL[current_month]} patterns?",
        expanded=False
    ):
        mr_so = load_mr_so(currency)

        # Identify months that match the current equity regime
        if equity_val != "Unknown":
            regime_months_so = regimes_so[
                regimes_so["equity_regime"] == equity_val
            ].index
            regime_label_so = f"{equity_val} equity"
        else:
            regime_months_so = regimes_so[
                regimes_so["rate_regime"] == rate_val_r
            ].index
            regime_label_so = f"{rate_val_r} rates"

        mr_regime_so = mr_so[mr_so.index.isin(regime_months_so)]

        # Compare top 8 series: unconditional average vs regime-filtered average
        top_so = stats_clean[
            stats_clean["month"] == current_month
        ].nlargest(8, "consistency_score")["name"].tolist()

        compare_rows = []
        for s in top_so:
            if s not in mr_so.columns:
                continue
            all_vals    = mr_so[s][mr_so[s].index.month == current_month].dropna()
            regime_vals = (
                mr_regime_so[s][mr_regime_so[s].index.month == current_month].dropna()
                if s in mr_regime_so.columns else pd.Series()
            )
            if len(all_vals) < 3:
                continue
            direction_flips = (
                len(regime_vals) >= 3 and
                (all_vals.mean() > 0) != (regime_vals.mean() > 0)
            )
            compare_rows.append({
                "Series":           s,
                "Unconditional":    f"{all_vals.mean()*100:+.2f}%",
                regime_label_so:    f"{regime_vals.mean()*100:+.2f}%" if len(regime_vals) >= 3 else "—",
                "Regime n":         len(regime_vals),
                "Direction change": "⚠️ Flips" if direction_flips else "✅ Holds",
            })

        if compare_rows:
            st.markdown(
                f'''<p style="font-size:0.85rem;color:{THEME["text_secondary"]};">
                ⚠️ Flips = pattern reverses direction in current regime vs
                unconditional average. ✅ Holds = pattern holds in same direction.
                </p>''',
                unsafe_allow_html=True
            )
            st.dataframe(
                pd.DataFrame(compare_rows),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Insufficient regime data for comparison.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── OUTLOOK TABS: CURRENT + NEXT TWO MONTHS ───────────────────────────────────
month_tabs = st.tabs([
    f"{'▶ ' if i == 0 else ''}{label}{' (Current)' if i == 0 else ''}"
    for i, label in enumerate(outlook_labels)
])

for tab, month_num, month_label in zip(month_tabs, outlook_months, outlook_labels):
    with tab:

        # Filter to this month, minimum 10 years of observations for reliability
        month_stats = stats_clean[stats_clean["month"] == month_num].copy()
        month_stats = month_stats[month_stats["n_obs"] >= 10].copy()
        month_stats = month_stats.dropna(subset=["consistency_score"])
        month_stats = month_stats.sort_values("consistency_score", ascending=False)

        if month_stats.empty:
            st.info(f"No sufficient data for {month_label}.")
            continue

        # Summary counts
        strong_bull  = month_stats[
            (month_stats["consistency_score"] >= 0.65) &
            (month_stats[metric_col] > 0)
        ]
        strong_bear  = month_stats[
            (month_stats["consistency_score"] >= 0.65) &
            (month_stats[metric_col] < 0)
        ]
        sig_patterns = month_stats[month_stats["p_value"] < 0.10]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Patterns", len(month_stats))
        c2.metric("Strong Bullish (≥0.65)", len(strong_bull))
        c3.metric("Strong Bearish (≥0.65)", len(strong_bear))
        c4.metric("Statistically Significant", len(sig_patterns))

        st.markdown("<br>", unsafe_allow_html=True)

        # ── TOP BULLISH ───────────────────────────────────────────────────────
        st.markdown(
            f'''<div class="section-header">
            Top Bullish Signals — {month_label}</div>''',
            unsafe_allow_html=True
        )

        top_bull = month_stats[month_stats[metric_col] > 0].head(10)

        if not top_bull.empty:
            # Bar chart of top bullish patterns
            fig_bull = go.Figure()
            fig_bull.add_trace(go.Bar(
                x=top_bull["name"],
                y=top_bull[metric_col] * 100,
                marker_color=THEME["positive"],
                opacity=0.85,
                text=[f"+{v*100:.2f}%" for v in top_bull[metric_col]],
                textposition="outside",
                textfont=dict(size=9),
                customdata=top_bull[["win_rate","consistency_score","n_obs"]].values,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Avg Return: %{y:.2f}%<br>"
                    "Win Rate: %{customdata[0]:.0%}<br>"
                    "Consistency Score: %{customdata[1]:.3f}<br>"
                    "Years of data: %{customdata[2]:.0f}<br>"
                    "<extra></extra>"
                ),
            ))
            fig_bull.update_layout(
                paper_bgcolor=THEME["bg"], plot_bgcolor=THEME["bg"],
                font=dict(family=THEME["font"], color=THEME["text_primary"]),
                xaxis=dict(showgrid=False, tickfont=dict(size=9), tickangle=30),
                yaxis=dict(
                    showgrid=True, gridcolor=THEME["border"],
                    ticksuffix="%", zeroline=True,
                    zerolinecolor=THEME["border"]
                ),
                margin=dict(l=20, r=20, t=20, b=100),
                height=350, showlegend=False,
            )
            st.plotly_chart(fig_bull, use_container_width=True)

            # Detailed table with confidence traffic light
            bull_table = top_bull[[
                "name", "asset_class", metric_col,
                "win_rate", "n_obs", "p_value", "consistency_score"
            ]].copy()
            bull_table.columns = [
                "Series", "Asset Class", "Avg Return",
                "Win Rate", "Years", "p-value", "Score"
            ]

            # Traffic light: green = strong and significant,
            # amber = moderate, red = weak
            def confidence_light(row):
                try:
                    score = float(row["Score"])
                    pval  = float(row["p-value"]) if row["p-value"] != "—" else 1.0
                except Exception:
                    return "🔴 Weak"
                if score >= 0.65 and pval < 0.10:
                    return "🟢 Strong"
                elif score >= 0.45 or pval < 0.20:
                    return "🟡 Moderate"
                else:
                    return "🔴 Weak"

            bull_table["Avg Return"] = bull_table["Avg Return"].map(
                lambda x: f"+{x*100:.2f}%"
            )
            bull_table["Win Rate"] = bull_table["Win Rate"].map(
                lambda x: f"{x*100:.0f}%"
            )
            bull_table["p-value"] = bull_table["p-value"].map(
                lambda x: f"{x:.3f}" if pd.notna(x) else "—"
            )
            bull_table["Score"] = bull_table["Score"].map(lambda x: f"{x:.3f}")
            bull_table["Years"] = bull_table["Years"].map(lambda x: str(int(x)))
            bull_table["Signal"] = bull_table.apply(confidence_light, axis=1)

            bull_table = bull_table[[
                "Signal", "Series", "Asset Class",
                "Avg Return", "Win Rate", "Years", "p-value", "Score"
            ]]
            st.dataframe(bull_table, use_container_width=True, hide_index=True)

            st.markdown(
                f'''<p style="font-size:0.75rem;color:{THEME["text_muted"]};">
                🟢 Strong = Score ≥ 0.65 and p &lt; 0.10 ·
                🟡 Moderate = Score ≥ 0.45 or p &lt; 0.20 ·
                🔴 Weak = below both thresholds ·
                Years = number of observations. Fewer years = less certainty.
                Patterns with fewer than 10 years excluded.
                </p>''',
                unsafe_allow_html=True
            )
        else:
            st.info(f"No bullish patterns found for {month_label}.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── TOP BEARISH ───────────────────────────────────────────────────────
        st.markdown(
            f'''<div class="section-header">
            Top Bearish Signals — {month_label} (Seasonal Headwinds)</div>''',
            unsafe_allow_html=True
        )

        top_bear = month_stats[month_stats[metric_col] < 0].head(5)

        if not top_bear.empty:
            bear_table = top_bear[[
                "name", "asset_class", metric_col,
                "win_rate", "n_obs", "p_value", "consistency_score"
            ]].copy()
            bear_table.columns = [
                "Series", "Asset Class", "Avg Return",
                "Win Rate", "Years", "p-value", "Score"
            ]
            bear_table["Avg Return"] = bear_table["Avg Return"].map(
                lambda x: f"{x*100:.2f}%"
            )
            bear_table["Win Rate"] = bear_table["Win Rate"].map(
                lambda x: f"{x*100:.0f}%"
            )
            bear_table["p-value"] = bear_table["p-value"].map(
                lambda x: f"{x:.3f}" if pd.notna(x) else "—"
            )
            bear_table["Score"] = bear_table["Score"].map(lambda x: f"{x:.3f}")
            bear_table["Years"] = bear_table["Years"].map(lambda x: str(int(x)))
            st.dataframe(bear_table, use_container_width=True, hide_index=True)
        else:
            st.info(f"No significant bearish patterns for {month_label}.")

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── ASSET CLASS SUMMARY ───────────────────────────────────────────────
        # Summary cards showing average return direction per asset class
        # for this month. Only investable classes shown (Macro/Vol excluded).
        st.markdown(
            f'''<div class="section-header">
            Asset Class Summary — {month_label}</div>''',
            unsafe_allow_html=True
        )

        ROTATION_CLASSES = ["Equity", "Commodity", "Fixed Income", "FX", "Mutual Fund"]
        ac_data = month_stats[month_stats["asset_class"].isin(ROTATION_CLASSES)].copy()

        if not ac_data.empty:
            ac_summary = (
                ac_data.groupby("asset_class")
                .agg(
                    avg_return=(metric_col, "mean"),
                    n_series=("name", "count"),
                    pct_positive=(metric_col, lambda x: (x > 0).mean()),
                )
                .reset_index()
                .sort_values("avg_return", ascending=False)
            )

            # Find best single series per asset class
            for ac in ac_summary["asset_class"]:
                ac_rows = ac_data[ac_data["asset_class"] == ac]
                best    = ac_rows.nlargest(1, metric_col)["name"].values
                ac_summary.loc[
                    ac_summary["asset_class"] == ac, "best_series"
                ] = best[0] if len(best) > 0 else "—"

            summary_cols = st.columns(len(ac_summary))
            for col, (_, row) in zip(summary_cols, ac_summary.iterrows()):
                direction = "▲" if row["avg_return"] > 0 else "▼"
                color     = THEME["positive"] if row["avg_return"] > 0 else THEME["negative"]
                best_name = str(row.get("best_series", "—"))[:28]
                col.markdown(
                    f'''<div style="background:{THEME["surface"]};
                    border:1px solid {THEME["border"]};
                    border-top:4px solid {color};
                    border-radius:8px;padding:0.9rem;text-align:center;">
                    <div style="font-size:0.8rem;font-weight:600;
                    color:{THEME["text_secondary"]};margin-bottom:0.3rem;">
                    {row["asset_class"]}</div>
                    <div style="font-size:1.3rem;font-weight:700;color:{color};">
                    {direction} {abs(row["avg_return"])*100:.2f}%</div>
                    <div style="font-size:0.72rem;color:{THEME["text_muted"]};
                    margin-top:0.3rem;">
                    {row["pct_positive"]*100:.0f}% of series positive</div>
                    <div style="font-size:0.72rem;color:{THEME["text_muted"]};">
                    Best: {best_name}</div>
                    </div>''',
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'''<p style="font-size:0.78rem;color:{THEME["text_muted"]};
            font-style:italic;">
            Seasonal patterns are based on historical averages and do not predict
            future returns. Use alongside fundamental and macro analysis.
            Consistency Score ≥ 0.65 and p-value &lt; 0.10 indicates a
            historically strong and statistically significant pattern.
            </p>''',
            unsafe_allow_html=True
        )
