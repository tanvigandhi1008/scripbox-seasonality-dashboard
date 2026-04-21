import streamlit as st
import pandas as pd

# ── Investability tier labels ─────────────────────────────────────────────────
TIER_LABELS = {
    "1": "India Direct",
    "2": "International (via FOF / LRS)",
    "3": "Reference Only",
}

TIER_DESCRIPTIONS = {
    "1": "Assets you can buy directly on NSE, BSE, MCX, or via Indian MF platforms. No special setup needed.",
    "2": "Assets accessible via Indian feeder funds (FOFs) or the Liberalised Remittance Scheme (LRS) through platforms like Vested or INDmoney.",
    "3": "Market data series used for macro context and analysis. These are rates, spreads, and indicators — not directly investable instruments.",
}

# Sub-class display names — maps raw sub_class values to cleaner labels
SUBCLASS_DISPLAY = {
    # Equity
    "Indian Broad Index":       "Broad Index",
    "Indian Sector Index":      "Sector Index",
    "Indian Size Segment":      "Size Segment",
    "Developed Market Index":   "Developed Market",
    "Emerging Market Index":    "Emerging Market",
    "Sector ETF":               "US Sector ETF",
    "Factor ETF":               "US Factor ETF",
    "Thematic ETF":             "Thematic ETF",
    "Regional ETF":             "Regional ETF",
    # Commodity
    "Precious Metal":           "Precious Metal",
    "Energy":                   "Energy",
    "Base Metal":               "Base Metal",
    "Agriculture":              "Agriculture",
    "Commodity Index":          "Commodity Index",
    # FX
    "INR Cross":                "INR Cross Rates",
    "EM Pair":                  "EM Currency Pairs",
    "Major Pair":               "Major Pairs",
    "Dollar Index":             "Dollar Index",
    # Fixed Income
    "Indian Sovereign":         "Indian Sovereign",
    "US Treasury Yield":        "US Treasury Yields",
    "Bond ETF":                 "Bond ETFs",
    "Credit Spread":            "Credit Spreads",
    "Yield Curve Spread":       "Yield Curve",
    "Sovereign Yield":          "Sovereign Yields",
    "Inflation Expectation":    "Inflation Expectations",
    "Real Yield":               "Real Yields",
    "Policy Rate":              "Policy Rates",
    # Mutual Fund
    "Equity MF":                "Equity Funds",
    "Hybrid MF":                "Hybrid Funds",
    "Debt MF":                  "Debt Funds",
    "International MF":         "International FOF",
    # Volatility / Macro
    "Volatility Index":         "Volatility Index",
    "Equity Volatility":        "Equity Volatility",
    "Commodity Volatility":     "Commodity Volatility",
    "Real Assets":              "Real Assets",
    "Trade Indicator":          "Trade Indicator",
    "Growth":                   "Growth",
    "Inflation":                "Inflation",
    "Labour Market":            "Labour Market",
    "Consumption":              "Consumption",
    "Housing":                  "Housing",
    "Sentiment":                "Sentiment",
    "Liquidity":                "Liquidity",
    "Commodity Supply":         "Commodity Supply",
    "Energy Price":             "Energy Price",
}


def _init_session_state():
    """Initialise all filter session state keys with safe defaults."""
    defaults = {
        "inv_tier":      "1",
        "asset_classes": [],   # empty = all
        "geographies":   [],   # empty = all
        "sub_classes":   [],   # empty = all
        # existing controls — preserve them
        "currency":          "local",
        "lookback_years":    25,
        "sig_filter":        "All patterns",
        "regime_filter":     "All regimes",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_filter_bar(meta: pd.DataFrame, page_key: str = "default") -> pd.DataFrame:
    """
    Render the three-layer filter strip at the top of a page.
    Returns a filtered copy of meta containing only the series
    that match all selected filters.

    Parameters
    ----------
    meta      : full metadata DataFrame (must have investability_tier column)
    page_key  : unique string per page to avoid widget key collisions

    Usage in any page
    -----------------
    from utils.filters import render_filter_bar
    meta = load_metadata()
    meta = render_filter_bar(meta, page_key="overview")
    # Then use filtered meta to drive all charts on that page
    """
    _init_session_state()

    # ── LAYER 1: Investor View tabs ───────────────────────────────────────────
    st.markdown(
        '''<div style="margin-bottom:0.4rem">
        <span style="color:#6b748a;font-size:0.72rem;letter-spacing:0.08em;
        text-transform:uppercase">Investor View</span></div>''',
        unsafe_allow_html=True
    )

    tier_options = ["1", "2", "3"]
    tier_display = [TIER_LABELS[t] for t in tier_options]

    current_tier_idx = tier_options.index(
        st.session_state.get("inv_tier", "1")
    )

    selected_tier_label = st.radio(
        label="inv_tier_radio",
        options=tier_display,
        index=current_tier_idx,
        horizontal=True,
        label_visibility="collapsed",
        key=f"inv_tier_radio_{page_key}",
    )
    selected_tier = tier_options[tier_display.index(selected_tier_label)]
    st.session_state["inv_tier"] = selected_tier

    # Tier description note
    tier_color = {"1": "#2ecc71", "2": "#2980b9", "3": "#f39c12"}[selected_tier]
    st.markdown(
        f'''<div style="background:#0d1117;border:1px solid #1e2436;
        border-left:3px solid {tier_color};border-radius:5px;
        padding:0.45rem 0.85rem;margin-bottom:0.75rem;
        color:#8a9bc0;font-size:0.78rem">{TIER_DESCRIPTIONS[selected_tier]}</div>''',
        unsafe_allow_html=True
    )

    # Filter metadata to selected tier
    if "investability_tier" in meta.columns:
        tier_meta = meta[meta["investability_tier"].astype(str) == selected_tier].copy()
    else:
        # Fallback if old metadata without the column
        tier_meta = meta.copy()

    if tier_meta.empty:
        st.warning("No series found for this investor view.")
        return tier_meta

    # ── LAYER 2: Asset Class + Geography (side by side) ───────────────────────
    col_ac, col_geo = st.columns([1, 1])

    available_classes = sorted(tier_meta["asset_class"].dropna().unique().tolist())
    with col_ac:
        selected_classes = st.multiselect(
            "Asset Class",
            options=available_classes,
            default=[],
            placeholder="All asset classes",
            key=f"asset_class_ms_{page_key}",
        )
    st.session_state["asset_classes"] = selected_classes

    # Apply asset class filter before computing geography options
    if selected_classes:
        class_meta = tier_meta[tier_meta["asset_class"].isin(selected_classes)]
    else:
        class_meta = tier_meta

    available_geos = sorted(class_meta["geography"].dropna().unique().tolist())
    with col_geo:
        selected_geos = st.multiselect(
            "Geography",
            options=available_geos,
            default=[],
            placeholder="All geographies",
            key=f"geography_ms_{page_key}",
        )
    st.session_state["geographies"] = selected_geos

    # Apply geography filter
    if selected_geos:
        geo_meta = class_meta[class_meta["geography"].isin(selected_geos)]
    else:
        geo_meta = class_meta

    # ── LAYER 3: Sub-class ────────────────────────────────────────────────────
    available_subs_raw = sorted(geo_meta["sub_class"].dropna().unique().tolist())
    available_subs_display = [
        SUBCLASS_DISPLAY.get(s, s) for s in available_subs_raw
    ]
    # Build reverse map for selected values
    display_to_raw = {
        SUBCLASS_DISPLAY.get(s, s): s for s in available_subs_raw
    }

    selected_subs_display = st.multiselect(
        "Sub-category",
        options=available_subs_display,
        default=[],
        placeholder="All sub-categories",
        key=f"subclass_ms_{page_key}",
    )

    selected_subs_raw = [display_to_raw[d] for d in selected_subs_display]
    st.session_state["sub_classes"] = selected_subs_raw

    # Apply sub-class filter
    if selected_subs_raw:
        final_meta = geo_meta[geo_meta["sub_class"].isin(selected_subs_raw)]
    else:
        final_meta = geo_meta

    # ── Summary line ──────────────────────────────────────────────────────────
    n_shown = len(final_meta)
    n_total = len(meta)
    st.markdown(
        f'''<div style="color:#4a5575;font-size:0.72rem;
        margin-bottom:0.5rem;margin-top:0.1rem">
        Showing {n_shown} of {n_total} series</div>''',
        unsafe_allow_html=True
    )

    st.markdown('<hr style="border:none;border-top:1px solid #1e2436;margin:0.5rem 0 1.2rem 0">',
                unsafe_allow_html=True)

    return final_meta.reset_index(drop=True)


def filter_stats(stats: pd.DataFrame, filtered_meta: pd.DataFrame) -> pd.DataFrame:
    """
    Filter a seasonality stats DataFrame to only include series
    that appear in filtered_meta. Call this after render_filter_bar().

    Parameters
    ----------
    stats        : seasonality_stats DataFrame (must have 'name' or 'series_name' column)
    filtered_meta: the filtered metadata returned by render_filter_bar()
    """
    name_col = "name" if "name" in stats.columns else "series_name"
    valid_names = set(filtered_meta["name"].tolist())
    return stats[stats[name_col].isin(valid_names)].copy()


def filter_returns(returns: pd.DataFrame, filtered_meta: pd.DataFrame) -> pd.DataFrame:
    """
    Filter a monthly returns DataFrame (columns = series names)
    to only include columns present in filtered_meta.
    """
    valid_names = set(filtered_meta["name"].tolist())
    valid_cols  = [c for c in returns.columns if c in valid_names]
    return returns[valid_cols].copy()
