
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 08_Indian_Investor_View.py
# PURPOSE: Curated view of seasonal patterns most relevant to Indian investors.
#
# FILTERING RULES:
#   - Indian equity, MCX commodities, USD/INR: price returns in % terms
#   - India 10Y Government Bond: yield series shown in basis points (bps)
#     with clear labelling — displayed standalone, not mixed with % series
#   - International section (Global scope): price-return series only via
#     filter_for_multiasset — yield series excluded for comparability
#   - Macro and Volatility: excluded from all views on this page
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

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Indian Investor View · Scripbox Seasonality",
    page_icon="🇮🇳",
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

metric_col   = "avg_return" if heatmap_metric == "Average Return" else "median_return"
metric_label = heatmap_metric

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Indian Investor View</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Seasonal patterns most relevant to Indian investors ·
    {scope} scope · {"INR" if currency == "inr" else "Local Currency"} ·
    {metric_label}
    </div>''',
    unsafe_allow_html=True
)

st.markdown(
    f'''<div class="info-card">
    This page brings together the most actionable seasonal signals for an
    Indian investor — domestic equity indices, MCX commodities in INR,
    rupee behaviour, Indian bond yields, and mutual fund categories.
    In Global scope, internationally accessible ETFs are shown separately.
    Use individual asset class pages for deeper analysis.
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 1: INDIAN EQUITY INDICES ─────────────────────────────────────────
st.markdown('''<div class="section-header">Indian Equity Indices</div>''',
            unsafe_allow_html=True)

INDIAN_EQUITY = [
    "Nifty 50", "Sensex", "Nifty Next 50", "Nifty 100",
    "Nifty 500", "Nifty Midcap 150"
]

indian_eq_stats = stats_all[stats_all["name"].isin(INDIAN_EQUITY)].copy()

if not indian_eq_stats.empty:
    pivot_ieq = indian_eq_stats.pivot_table(
        index="name", columns="month", values=metric_col, aggfunc="mean"
    )
    pivot_ieq = pivot_ieq.reindex(columns=range(1, 13))
    pivot_ieq.columns = MONTHS
    pivot_ieq = pivot_ieq.reindex(
        [n for n in INDIAN_EQUITY if n in pivot_ieq.index]
    )
    fig = build_heatmap(pivot_ieq, value_col_label="Return (%)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"{len(pivot_ieq)} series · Indian broad market indices · "
        f"Values in % · {metric_label}"
    )
else:
    st.info("No Indian equity data available under current filters.")

# ── SECTION 2: INDIAN SECTOR INDICES ─────────────────────────────────────────
st.markdown('''<div class="section-header">Indian Sector Indices</div>''',
            unsafe_allow_html=True)

indian_sector_stats = stats_all[
    (stats_all["asset_class"] == "Equity") &
    (stats_all["sub_class"] == "Indian Sector Index")
].copy()

if not indian_sector_stats.empty:
    pivot_isec = indian_sector_stats.pivot_table(
        index="name", columns="month", values=metric_col, aggfunc="mean"
    )
    pivot_isec = pivot_isec.reindex(columns=range(1, 13))
    pivot_isec.columns = MONTHS
    fig = build_heatmap(pivot_isec, value_col_label="Return (%)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"{len(pivot_isec)} series · Indian sector indices · "
        f"Values in % · {metric_label}"
    )
else:
    st.info("No Indian sector data available under current filters.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 3: MCX COMMODITIES (INR) ─────────────────────────────────────────
# All MCX series are price-return series in INR — directly comparable
st.markdown('''<div class="section-header">MCX Commodities (INR)</div>''',
            unsafe_allow_html=True)

MCX_SERIES = [
    "MCX Gold INR (Synthetic)", "MCX Silver INR (Synthetic)",
    "MCX Crude Oil INR (Synthetic)", "MCX Natural Gas INR (Synthetic)",
    "MCX Copper INR (Synthetic)", "MCX Zinc INR (Synthetic)",
    "MCX Aluminium INR (Synthetic)",
]
# Also include international crude as reference if available
INTL_CRUDE = ["Crude Oil Brent", "Crude Oil WTI"]
all_comm_names = MCX_SERIES + INTL_CRUDE

comm_stats = stats_all[stats_all["name"].isin(all_comm_names)].copy()
# Keep only series that actually exist in current scope
comm_stats = comm_stats[comm_stats["name"].isin(stats_all["name"].values)]

if not comm_stats.empty:
    if any(s in comm_stats["name"].values for s in MCX_SERIES):
        st.markdown(
            '''<div class="synthetic-note">
            MCX series are synthetically constructed from international spot
            prices converted to INR using USD/INR exchange rates. They
            approximate what an Indian investor holding these commodities
            experiences in rupee terms.
            </div>''',
            unsafe_allow_html=True
        )

    pivot_comm = comm_stats.pivot_table(
        index="name", columns="month", values=metric_col, aggfunc="mean"
    )
    pivot_comm = pivot_comm.reindex(columns=range(1, 13))
    pivot_comm.columns = MONTHS
    fig = build_heatmap(pivot_comm, value_col_label="Return (%)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"{len(pivot_comm)} series · MCX Commodities in INR + International · "
        f"Values in % · {metric_label}"
    )
else:
    st.info("No commodity data available under current filters.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 4: RUPEE AND INDIAN FIXED INCOME ──────────────────────────────────
# USD/INR: price return series — shown in %
# India 10Y Government Bond: yield series — shown in basis points (bps)
# These two are shown in SEPARATE charts because they use different units.
# Never mix yield series and price series on the same axis.
st.markdown('''<div class="section-header">Rupee and Indian Fixed Income</div>''',
            unsafe_allow_html=True)

# FX always uses local currency stats regardless of sidebar toggle
# because converting an exchange rate to INR is not meaningful
fx_stats_local, _ = prepare_stats("local", scope, lookback)
rupee_stats = fx_stats_local[fx_stats_local["name"] == "USD/INR"].copy()

# India 10Y bond from main stats
bond_stats = stats_all[stats_all["name"] == "India 10Y Government Bond"].copy()

col_rupee, col_bond = st.columns(2)

with col_rupee:
    st.markdown(
        f'''<p style="font-size:0.85rem;font-weight:600;
        color:{THEME["text_secondary"]};margin-bottom:0.4rem;">
        USD/INR — Monthly Return (%)</p>
        <p style="font-size:0.78rem;color:{THEME["text_muted"]};
        margin-bottom:0.5rem;">
        Positive = rupee weakened (more INR per USD) ·
        Negative = rupee strengthened</p>''',
        unsafe_allow_html=True
    )
    if not rupee_stats.empty:
        rupee_month = rupee_stats.sort_values("month")
        fig_rupee = go.Figure()
        fig_rupee.add_trace(go.Bar(
            x=MONTHS,
            y=rupee_month[metric_col] * 100,
            # For USD/INR: positive means rupee weakened = bad for Indian
            # investors importing or investing abroad = shown in red
            marker_color=[
                THEME["negative"] if v >= 0 else THEME["positive"]
                for v in rupee_month[metric_col]
            ],
            text=[f"{v*100:+.2f}%" for v in rupee_month[metric_col]],
            textposition="outside",
            textfont=dict(size=8),
            name="USD/INR",
        ))
        fig_rupee.update_layout(
            paper_bgcolor=THEME["bg"], plot_bgcolor=THEME["bg"],
            font=dict(family=THEME["font"], color=THEME["text_primary"]),
            xaxis=dict(showgrid=False, tickfont=dict(size=10)),
            yaxis=dict(
                showgrid=True, gridcolor=THEME["border"],
                ticksuffix="%", zeroline=True,
                zerolinecolor=THEME["border"],
                title=dict(text="Monthly Return (%)", font=dict(size=10)),
            ),
            margin=dict(l=10, r=10, t=10, b=40),
            height=280, showlegend=False,
        )
        st.plotly_chart(fig_rupee, use_container_width=True)
    else:
        st.info("USD/INR data not available under current filters.")

with col_bond:
    st.markdown(
        f'''<p style="font-size:0.85rem;font-weight:600;
        color:{THEME["text_secondary"]};margin-bottom:0.4rem;">
        India 10Y Government Bond — Monthly Yield Change (bps)</p>
        <p style="font-size:0.78rem;color:{THEME["text_muted"]};
        margin-bottom:0.5rem;">
        Positive = yield rose (bond prices fell) ·
        1 bps = 0.01 percentage point</p>''',
        unsafe_allow_html=True
    )
    if not bond_stats.empty:
        bond_month = bond_stats.sort_values("month")

        # India 10Y is a yield series stored as decimal changes
        # (e.g. 0.002 = 0.2 percentage points = 20 bps)
        # Multiply by 10000 to display in basis points
        # Example: 0.002 * 10000 = 20 bps — correct and clear
        BPS_MULTIPLIER = 10000

        fig_bond = go.Figure()
        fig_bond.add_trace(go.Bar(
            x=MONTHS,
            y=bond_month[metric_col] * BPS_MULTIPLIER,
            # Rising yield = bond prices fell = negative for bond holders = red
            # Falling yield = bond prices rose = positive for bond holders = green
            marker_color=[
                THEME["negative"] if v >= 0 else THEME["positive"]
                for v in bond_month[metric_col]
            ],
            text=[f"{v*BPS_MULTIPLIER:+.1f} bps" for v in bond_month[metric_col]],
            textposition="outside",
            textfont=dict(size=8),
            name="India 10Y",
        ))
        fig_bond.update_layout(
            paper_bgcolor=THEME["bg"], plot_bgcolor=THEME["bg"],
            font=dict(family=THEME["font"], color=THEME["text_primary"]),
            xaxis=dict(showgrid=False, tickfont=dict(size=10)),
            yaxis=dict(
                showgrid=True, gridcolor=THEME["border"],
                ticksuffix=" bps", zeroline=True,
                zerolinecolor=THEME["border"],
                title=dict(text="Yield Change (bps)", font=dict(size=10)),
            ),
            margin=dict(l=10, r=10, t=10, b=40),
            height=280, showlegend=False,
        )
        st.plotly_chart(fig_bond, use_container_width=True)
    else:
        st.info("India 10Y bond data not available under current filters.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 5: INDIAN MUTUAL FUND CATEGORIES ──────────────────────────────────
st.markdown('''<div class="section-header">Indian Mutual Fund Categories</div>''',
            unsafe_allow_html=True)

mf_stats = stats_all[stats_all["asset_class"] == "Mutual Fund"].copy()

if not mf_stats.empty:
    st.markdown(
        f'''<div class="synthetic-note">
        <strong>Data coverage note:</strong> SEBI standardised mutual fund
        categories in October 2017. Category-average NAV data from AMFI
        is therefore only available from approximately 2008–2013 depending
        on the category. Most MF series have 10–17 years of data, not 25.
        Patterns shown are based on this shorter history and should be
        interpreted with more caution than equity or commodity series which
        have the full 25-year dataset.
        </div>''',
        unsafe_allow_html=True
    )
    MF_SUB_ORDER = ["Equity MF", "Hybrid MF", "Debt MF", "International MF"]
    available_mf_subs = [s for s in MF_SUB_ORDER if s in mf_stats["sub_class"].values]

    mf_tabs = st.tabs(available_mf_subs)
    for mf_tab, mf_sub in zip(mf_tabs, available_mf_subs):
        with mf_tab:
            mf_sub_stats = mf_stats[mf_stats["sub_class"] == mf_sub].copy()
            if mf_sub_stats.empty:
                st.info(f"No data for {mf_sub}.")
                continue
            pivot_mf = mf_sub_stats.pivot_table(
                index="name", columns="month",
                values=metric_col, aggfunc="mean"
            )
            pivot_mf = pivot_mf.reindex(columns=range(1, 13))
            pivot_mf.columns = MONTHS
            fig = build_heatmap(pivot_mf, value_col_label="Return (%)")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"{len(pivot_mf)} categories · {mf_sub} · "
                f"Values in % · {metric_label}"
            )
else:
    st.info("No mutual fund data available under current filters.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 6: INTERNATIONALLY ACCESSIBLE ASSETS (GLOBAL SCOPE ONLY) ─────────
if scope == "Global (LRS / International)":
    st.markdown(
        '''<div class="section-header">Internationally Accessible Assets (LRS / FoF)</div>''',
        unsafe_allow_html=True
    )

    st.markdown(
        f'''<div class="info-card">
        Accessible via LRS (up to USD 250,000/year) or Indian AMC
        international fund-of-funds. All values are price returns in %
        — yield series excluded for comparability.
        Switch to Domestic scope to hide this section.
        </div>''',
        unsafe_allow_html=True
    )

    # Apply multi-asset filter to international section
    # so yield series do not appear here either
    intl_stats = filter_for_multiasset(stats_all)
    intl_stats = intl_stats[
        intl_stats["investability"].isin(["international", "international_etf"])
    ].copy()

    if not intl_stats.empty:
        INTL_AC_ORDER = ["Equity", "Fixed Income", "Commodity", "FX"]
        available_intl_acs = [
            ac for ac in INTL_AC_ORDER
            if ac in intl_stats["asset_class"].values
        ]

        intl_tabs = st.tabs(available_intl_acs)
        for itab, iac in zip(intl_tabs, available_intl_acs):
            with itab:
                iac_stats = intl_stats[intl_stats["asset_class"] == iac].copy()
                if iac_stats.empty:
                    st.info(f"No international {iac} data available.")
                    continue
                pivot_intl = iac_stats.pivot_table(
                    index="name", columns="month",
                    values=metric_col, aggfunc="mean"
                )
                pivot_intl = pivot_intl.reindex(columns=range(1, 13))
                pivot_intl.columns = MONTHS
                fig = build_heatmap(pivot_intl, value_col_label="Return (%)")
                st.plotly_chart(fig, use_container_width=True)
                st.caption(
                    f"{len(pivot_intl)} series · International {iac} · "
                    f"LRS / AMC FoF accessible · Values in % · {metric_label}"
                )
    else:
        st.info("No international series available under current filters.")

else:
    st.markdown(
        f'''<div style="background:{THEME["surface_alt"]};
        border:1px solid {THEME["border"]};
        border-radius:8px;padding:1.2rem;text-align:center;">
        <div style="font-weight:600;margin-bottom:0.4rem;">
        Want to see internationally accessible assets?</div>
        <div style="font-size:0.875rem;color:{THEME["text_secondary"]};">
        Switch Market Scope to <strong>Global (LRS / International)</strong>
        to see ETFs and assets accessible via LRS or international FoF.
        </div></div>''',
        unsafe_allow_html=True
    )

# ── METHODOLOGY EXPANDER ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("How to read this page — methodology and concepts"):
    st.markdown("""
**Why are USD/INR and India 10Y shown in separate charts with different units?**

USD/INR is a price return — the percentage change in the exchange rate
each month. This is directly comparable to equity and commodity returns.

India 10Y Government Bond is a yield series — it shows how much the
interest rate changed each month, measured in basis points (bps) where
1 bps = 0.01%. A yield change of +20 bps means the interest rate rose
by 0.20 percentage points. These two things cannot be shown on the same
axis with the same unit — they measure fundamentally different things.
Keeping them separate and clearly labelled prevents misinterpretation.

**What does a rising yield mean for Indian investors?**

When the India 10Y yield rises, existing bond prices fall (yields and
bond prices move in opposite directions). Rising yields also signal
tighter monetary conditions, which can pressure equity valuations.
For bond fund investors, rising yield months are typically unfavourable.

**MCX Commodities — why synthetic?**

Direct MCX historical price data is not freely available via public
APIs. We construct these series from international USD prices converted
to INR using USD/INR rates. This captures the actual experience of an
Indian investor holding these commodities in rupee terms.

**Indian mutual fund categories**

These show category-average returns across all funds in each SEBI
category. This removes individual fund manager skill and isolates the
seasonal pattern of the underlying asset class.

**LRS and international access**

Under the Liberalised Remittance Scheme, Indian residents can remit up
to USD 250,000 per year for international investment. International
fund-of-funds from Indian AMCs allow foreign exposure without a foreign
brokerage account. Both routes are shown in Global scope.
""")
