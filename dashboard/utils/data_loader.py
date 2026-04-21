
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

from pathlib import Path as _Path

def _resolve_base() -> str:
    """
    Returns the correct base path depending on environment.
    - Colab:  reads from Google Drive (original behaviour, unchanged)
    - Render: reads relative to this file inside the cloned repo
    """
    if _Path("/content/drive/MyDrive/seasonality_dashboard").exists():
        return "/content/drive/MyDrive/seasonality_dashboard"
    # On Render (or any server), this file lives at:
    # repo_root/dashboard/utils/data_loader.py
    # So parents[2] = repo_root
    return str(_Path(__file__).resolve().parents[2])

BASE      = _resolve_base()
PROCESSED = f"{BASE}/data/processed"
RAW       = f"{BASE}/data/raw"
ASSETS    = f"{BASE}/assets"

THEME = {
    "primary":        "#F47B20",
    "primary_light":  "#FFF4EB",
    "primary_mid":    "#FDDBB4",
    "bg":             "#FFFFFF",
    "surface":        "#F7F8FA",
    "surface_alt":    "#F0F2F5",
    "border":         "#E8EAF0",
    "text_primary":   "#1A1A2E",
    "text_secondary": "#6B748A",
    "text_muted":     "#9BA3B8",
    "positive":       "#1A7A4A",
    "positive_light": "#E8F5EE",
    "negative":       "#C0392B",
    "negative_light": "#FDECEA",
    "neutral":        "#F0F2F5",
    "font":           "DM Sans",
}

MONTHS     = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]
MONTH_FULL = {1:"January",2:"February",3:"March",4:"April",
               5:"May",6:"June",7:"July",8:"August",
               9:"September",10:"October",11:"November",12:"December"}

HEATMAP_COLORSCALE = [
    [0.00, "#7B1A1A"],
    [0.30, "#C0392B"],
    [0.47, "#F5C6C2"],
    [0.50, "#F0F2F5"],
    [0.53, "#C8E6D4"],
    [0.70, "#1A7A4A"],
    [1.00, "#0D4A28"],
]

# Series types stored in non-price units — excluded from multi-asset views
NON_PRICE_TYPES = {"yield", "spread", "rate", "index"}

# Asset classes that are economic indicators, not investable assets
NON_INVESTABLE_CLASSES = {"Macro", "Volatility"}

def inject_css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] {{
    font-family: "DM Sans", sans-serif;
    color: {THEME["text_primary"]};
}}
.main .block-container {{
    background: {THEME["bg"]};
    padding: 0.5rem 2.5rem 2rem 2.5rem;
    max-width: 1400px;
}}
section[data-testid="stSidebar"] {{
    background: {THEME["surface"]} !important;
    border-right: 1px solid {THEME["border"]} !important;
}}
section[data-testid="stSidebar"] * {{
    color: {THEME["text_primary"]} !important;
}}
.stMetric {{
    background: {THEME["surface"]} !important;
    border: 1px solid {THEME["border"]} !important;
    border-radius: 10px !important;
    padding: 1rem 1.2rem !important;
    border-left: 3px solid {THEME["primary"]} !important;
}}
.stMetric label {{
    color: {THEME["text_secondary"]} !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
.stMetric [data-testid="stMetricValue"] {{
    color: {THEME["text_primary"]} !important;
    font-weight: 600 !important;
}}
div[data-testid="stExpander"] {{
    border: 1px solid {THEME["border"]} !important;
    border-radius: 8px !important;
    background: {THEME["surface"]} !important;
}}
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    background: {THEME["surface_alt"]};
    border-radius: 8px;
    padding: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 500;
    color: {THEME["text_secondary"]};
}}
.stTabs [aria-selected="true"] {{
    background: {THEME["primary"]} !important;
    color: white !important;
}}
.stSelectbox > div > div {{
    border-color: {THEME["border"]} !important;
    border-radius: 8px !important;
}}
hr {{
    border-color: {THEME["border"]} !important;
    margin: 1rem 0 !important;
}}
.page-title {{
    font-size: 1.6rem;
    font-weight: 700;
    color: {THEME["text_primary"]};
    margin-bottom: 0.2rem;
}}
.page-subtitle {{
    font-size: 0.9rem;
    color: {THEME["text_secondary"]};
    margin-bottom: 1.5rem;
}}
.section-header {{
    font-size: 1rem;
    font-weight: 600;
    color: {THEME["text_primary"]};
    margin: 1.5rem 0 0.75rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid {THEME["primary_light"]};
}}
.info-card {{
    background: {THEME["primary_light"]};
    border: 1px solid {THEME["primary_mid"]};
    border-left: 4px solid {THEME["primary"]};
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin: 0.75rem 0;
    font-size: 0.875rem;
    color: {THEME["text_primary"]};
}}
.synthetic-note {{
    background: #FFF8E1;
    border: 1px solid #FFE082;
    border-left: 4px solid #F9A825;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin: 0.75rem 0;
    font-size: 0.875rem;
}}
.benchmark-badge {{
    display: inline-block;
    background: {THEME["surface_alt"]};
    border: 1px solid {THEME["border"]};
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 0.7rem;
    color: {THEME["text_secondary"]};
    font-family: "DM Mono", monospace;
    margin-left: 4px;
}}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_metadata():
    return pd.read_csv(f"{BASE}/data/metadata.csv")

@st.cache_data(ttl=300)
def load_monthly_returns(currency="local"):
    if currency == "inr":
        return pd.read_csv(f"{PROCESSED}/monthly_returns_inr.csv",
                           index_col=0, parse_dates=True)
    return pd.read_csv(f"{PROCESSED}/monthly_returns.csv",
                       index_col=0, parse_dates=True)

@st.cache_data(ttl=300)
def load_seasonality_stats(currency="local"):
    if currency == "inr":
        df = pd.read_csv(f"{PROCESSED}/seasonality_stats_inr.csv")
    else:
        df = pd.read_csv(f"{PROCESSED}/seasonality_stats.csv")
    if "series_name" in df.columns:
        df = df.rename(columns={"series_name": "name"})
    return df

@st.cache_data(ttl=300)
def load_regime_labels():
    return pd.read_csv(f"{PROCESSED}/regime_labels.csv",
                       index_col=0, parse_dates=True)

def filter_by_market_scope(meta, scope):
    if scope == "Domestic":
        allowed = {"domestic", "benchmark"}
    else:
        allowed = {"domestic", "benchmark", "international", "international_etf"}
    return meta[meta["investability"].isin(allowed)].copy()

def filter_for_multiasset(stats_df):
    """
    Removes series that cannot be shown alongside price returns in a
    multi-asset view. Specifically removes:
    - yield, spread, rate, index series (stored in bps not %)
    - Macro and Volatility asset classes (not investable assets)
    Use this on every page that combines multiple asset classes.
    """
    mask = (
        ~stats_df["series_type"].isin(NON_PRICE_TYPES) &
        ~stats_df["asset_class"].isin(NON_INVESTABLE_CLASSES)
    )
    return stats_df[mask].copy()

def prepare_stats(currency, scope, lookback_years=25):
    """
    Loads and filters seasonality stats for the given currency, scope,
    and lookback window. Returns (stats_df, meta_df).

    For the full 25-year history, returns pre-computed stats from CSV.
    For shorter windows, recomputes stats from raw monthly returns.
    """
    from scipy import stats as scipy_stats

    meta_all = load_metadata()
    meta     = filter_by_market_scope(meta_all, scope)
    visible  = set(meta["name"].tolist())

    if lookback_years >= 25:
        # Use pre-computed stats file for full history
        stats = load_seasonality_stats(currency)
        stats = stats[stats["name"].isin(visible)].copy()
        stats = stats.merge(
            meta[["name", "investability", "notes"]],
            on="name", how="left"
        )
        return stats, meta

    # For shorter lookback windows, recompute from raw monthly returns
    mr = load_monthly_returns(currency)
    cutoff_year = pd.Timestamp.today().year - lookback_years
    mr = mr[mr.index.year > cutoff_year]
    mr = mr[[c for c in mr.columns if c in visible]]

    MONTH_NAMES = {
        1:"January", 2:"February", 3:"March",    4:"April",
        5:"May",     6:"June",     7:"July",      8:"August",
        9:"September",10:"October",11:"November",12:"December"
    }
    MIN_OBS     = 5
    all_rows    = []
    meta_lookup = meta_all.set_index("name").to_dict("index")

    for col in mr.columns:
        for month_num in range(1, 13):
            mask   = mr.index.month == month_num
            clean  = mr.loc[mask, col].dropna()
            n_obs  = len(clean)
            m_info = meta_lookup.get(col, {})
            row = {
                "name":          col,
                "month":         month_num,
                "month_name":    MONTH_NAMES[month_num],
                "n_obs":         n_obs,
                "asset_class":   m_info.get("asset_class", ""),
                "sub_class":     m_info.get("sub_class", ""),
                "geography":     m_info.get("geography", ""),
                "currency":      m_info.get("currency", ""),
                "series_type":   m_info.get("series_type", ""),
                "avg_return":    float(clean.mean())             if n_obs >= MIN_OBS else float("nan"),
                "median_return": float(clean.median())           if n_obs >= MIN_OBS else float("nan"),
                "std_return":    float(clean.std())              if n_obs >= MIN_OBS else float("nan"),
                "win_rate":      float((clean > 0).sum() / n_obs) if n_obs >= MIN_OBS else float("nan"),
                "best_return":   float(clean.max())              if n_obs >= MIN_OBS else float("nan"),
                "worst_return":  float(clean.min())              if n_obs >= MIN_OBS else float("nan"),
                "best_year":     int(clean.idxmax().year)        if n_obs >= MIN_OBS else float("nan"),
                "worst_year":    int(clean.idxmin().year)        if n_obs >= MIN_OBS else float("nan"),
            }
            if n_obs >= 3:
                t, p = scipy_stats.ttest_1samp(clean, popmean=0)
                row["t_stat"]  = round(float(t), 4)
                row["p_value"] = round(float(p), 4)
            else:
                row["t_stat"]  = float("nan")
                row["p_value"] = float("nan")
            all_rows.append(row)

    stats = pd.DataFrame(all_rows)
    stats = stats.merge(
        meta[["name", "investability", "notes"]],
        on="name", how="left"
    )
    return stats, meta

def build_heatmap(pivot_df, value_col_label="Return (%)",
                  is_basis_points=False, already_in_bps=False, height=None):
    """
    Builds a Plotly heatmap from a pivot table.
    pivot_df: rows = series names, columns = month names (Jan..Dec)

    Three display modes:
    - Default (is_basis_points=False, already_in_bps=False):
        Values are decimal price returns (0.02 = 2%).
        Multiplied by 100 to display as %.
    - is_basis_points=True:
        Values are decimal yield changes (0.002 = 20 bps).
        Multiplied by 10000 to display as bps.
    - already_in_bps=True:
        Values are already in bps (e.g. 2.37 means 2.37 bps).
        Multiplied by 1. Use for yield/spread series from stats CSV
        which store changes as diff()*100, giving values in bps directly.

    Colour scale uses 5th-95th percentile to prevent outlier dominance.
    """
    import plotly.graph_objects as go

    if already_in_bps:
        multiplier = 1
        unit_label = "bps"
    elif is_basis_points:
        multiplier = 10000
        unit_label = "bps"
    else:
        multiplier = 100
        unit_label = "%"

    z    = pivot_df.values * multiplier
    flat = z[~np.isnan(z)]

    if len(flat) == 0:
        return go.Figure()

    abs_max = max(abs(np.percentile(flat, 5)),
                  abs(np.percentile(flat, 95)))
    abs_max = abs_max if abs_max > 0 else 1

    text = [[f"{v:+.1f}{unit_label}" if not np.isnan(v) else ""
             for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=MONTHS,
        y=pivot_df.index.tolist(),
        text=text,
        texttemplate="%{text}",
        textfont={"size": 9, "color": THEME["text_primary"]},
        colorscale=HEATMAP_COLORSCALE,
        zmin=-abs_max, zmax=abs_max, zmid=0,
        showscale=True,
        colorbar=dict(
            title=dict(text=value_col_label,
                       font=dict(size=10, color=THEME["text_secondary"])),
            tickfont=dict(color=THEME["text_secondary"], size=9),
            outlinewidth=0,
            bgcolor=THEME["bg"],
            thickness=12,
            len=0.8,
        ),
        xgap=2, ygap=1.5,
    ))

    fig.update_layout(
        paper_bgcolor=THEME["bg"],
        plot_bgcolor=THEME["bg"],
        font=dict(family=THEME["font"], color=THEME["text_primary"], size=11),
        xaxis=dict(
            side="top",
            tickfont=dict(size=11, color=THEME["text_secondary"]),
            showgrid=False,
        ),
        yaxis=dict(
            tickfont=dict(size=9, color=THEME["text_secondary"]),
            showgrid=False,
            autorange="reversed",
        ),
        margin=dict(l=10, r=80, t=40, b=20),
        height=height or max(380, len(pivot_df) * 24 + 80),
    )
    return fig

def render_sidebar():
    """
    Renders the sidebar with all global controls.
    Must be called at the top of every page.
    Uses key= parameter so Streamlit persists values in session_state.
    """
    st.sidebar.radio(
        "Market Scope",
        options=["Domestic", "Global (LRS / International)"],
        key="market_scope",
        help=(
            "Domestic: Indian markets + global reference benchmarks only.\n"
            "Global: adds LRS/FoF-accessible international ETFs and assets."
        ),
    )

    st.sidebar.markdown("---")

    st.sidebar.selectbox(
        "Currency View",
        options=["Local Currency", "INR"],
        key="currency_display",
    )
    st.session_state["currency"] = (
        "inr" if st.session_state.get("currency_display") == "INR"
        else "local"
    )

    st.sidebar.selectbox(
        "Lookback Window",
        options=["Max (25Y)", "20Y", "10Y", "5Y"],
        key="lookback_display",
    )
    st.session_state["lookback_years"] = {
        "Max (25Y)": 25, "20Y": 20, "10Y": 10, "5Y": 5
    }[st.session_state.get("lookback_display", "Max (25Y)")]

    st.sidebar.selectbox(
        "Significance Filter",
        options=["All patterns", "p < 0.10", "p < 0.05"],
        key="sig_filter",
    )

    st.sidebar.selectbox(
        "Heatmap Metric",
        options=["Average Return", "Median Return"],
        key="heatmap_metric",
    )

    st.sidebar.markdown("---")

    scope = st.session_state.get("market_scope", "Domestic")
    if scope == "Domestic":
        st.sidebar.caption(
            "Domestic mode: Indian markets + global reference benchmarks. "
            "Switch to Global to see internationally investable assets."
        )
    else:
        st.sidebar.caption(
            "Global mode: all investable assets visible. "
            "Benchmark series are reference indices, not directly investable."
        )
