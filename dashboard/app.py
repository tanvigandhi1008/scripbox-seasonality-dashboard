import streamlit as st
from utils.data_loader import inject_css, render_sidebar, THEME, load_metadata
import json
from pathlib import Path

st.set_page_config(
    page_title="Global Seasonality Dashboard",
    page_icon="\U0001f4c5",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
render_sidebar()

try:
    meta         = load_metadata()
    series_count = len(meta)
except Exception:
    series_count = 160

# Last updated timestamp
last_updated_ist = "Updated daily"
try:
    from utils.data_loader import PROCESSED
    log_path = Path(PROCESSED) / "refresh_log.json"
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
        last_updated_ist = log.get("last_updated_ist", last_updated_ist)
except Exception:
    pass

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center; padding: 3rem 2rem 1rem 2rem;">
    <div style="font-size:2rem; font-weight:700;
    color:{THEME['text_primary']}; margin-bottom:0.5rem;">
        Global Seasonality Dashboard
    </div>
    <div style="font-size:1rem; color:{THEME['text_secondary']};
    margin-bottom:0.5rem;">
        Recurring seasonal patterns across global and Indian asset classes
    </div>
    <div style="display:inline-block;
    background:{THEME['primary_light']};
    border:1px solid {THEME['primary_mid']};
    border-radius:20px;
    padding:0.3rem 1rem;
    font-size:0.82rem;
    color:{THEME['primary']};
    font-weight:600;
    margin-top:0.5rem;">
        Data as of {last_updated_ist}
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── ABOUT ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:{THEME['surface']};
border:1px solid {THEME['border']};
border-left:4px solid {THEME['primary']};
border-radius:10px;
padding:1.5rem 1.8rem;
margin-bottom:1.5rem;">
<div style="font-size:1rem;font-weight:700;
color:{THEME['text_primary']};margin-bottom:0.75rem;">
About this Dashboard
</div>
<div style="font-size:0.88rem;color:{THEME['text_secondary']};
line-height:1.85;">

Seasonality refers to the tendency of financial markets to behave
differently depending on the time of year. January might historically
be strong for equities. October might tend to be weak for gold.
These patterns do not repeat perfectly every year, but they repeat
often enough and consistently enough to be worth knowing about.
One of the most important questions in asset allocation is not just
what to invest in, but when conditions tend to favour certain asset
classes over others.

<br><br>

This dashboard is built to make those patterns visible, measurable,
and actionable. It covers {series_count} asset series spanning Indian
and global equities, fixed income, commodities, currencies, mutual fund
categories, volatility indices, and macroeconomic indicators, going
back to January 2000 where data is available. For every series and every
calendar month, the dashboard computes the average return, median return,
win rate, and statistical significance, so that genuine patterns can be
distinguished from noise.

<br><br>

Beyond calendar patterns, the dashboard also looks at how different macro
environments affect returns. Whether interest rates are rising or falling,
whether the rupee is strengthening or weakening, whether equity markets
are in a bull or bear phase. This makes it possible to filter patterns by
the conditions that most closely resemble today, and ask questions like:
which months have historically been strong for Nifty 50? Does gold tend
to do well in a weak rupee environment? How do Indian equities behave in
rate-rising regimes? What does the current macro regime imply for asset
allocation over the next few months? These are not questions that can be
answered quickly with standard market data tools. This dashboard was built
specifically to surface them in one place, updated automatically every day.

<br><br>

All data sources, calculation methods, and known data gaps are documented
transparently in the Data Library page.

</div>
</div>
""", unsafe_allow_html=True)

# ── HOW TO USE ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
<div style="background:{THEME['surface']};border:1px solid {THEME['border']};
border-left:4px solid {THEME['primary']};border-radius:10px;padding:1.2rem;
height:100%;">
<div style="font-weight:600;margin-bottom:0.4rem;">Use the sidebar to navigate</div>
<div style="font-size:0.85rem;color:{THEME['text_secondary']};">
Select Market Scope, Currency View, Lookback Window, and Significance Filter.
All settings apply across every page automatically.
</div>
</div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
<div style="background:{THEME['surface']};border:1px solid {THEME['border']};
border-left:4px solid {THEME['primary']};border-radius:10px;padding:1.2rem;
height:100%;">
<div style="font-weight:600;margin-bottom:0.4rem;">Domestic vs Global scope</div>
<div style="font-size:0.85rem;color:{THEME['text_secondary']};">
Domestic shows Indian markets and global reference benchmarks.
Global adds all LRS and FoF-accessible international assets.
</div>
</div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
<div style="background:{THEME['surface']};border:1px solid {THEME['border']};
border-left:4px solid {THEME['primary']};border-radius:10px;padding:1.2rem;
height:100%;">
<div style="font-weight:600;margin-bottom:0.4rem;">Interpreting the heatmaps</div>
<div style="font-size:0.85rem;color:{THEME['text_secondary']};">
Green cells indicate historically positive months. Red cells indicate weak months.
Use the significance filter to show only statistically reliable patterns.
</div>
</div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;padding:1.5rem 0 1rem 0;">
    <div style="font-size:0.82rem;color:{THEME['text_muted']};margin-bottom:0.4rem;">
        Built by <strong style="color:{THEME['text_secondary']};">Tanvi Gandhi</strong>
        and <strong style="color:{THEME['text_secondary']};">Rutuja Somvanshi</strong>
        &nbsp;·&nbsp; 2026
    </div>
    <div style="font-size:0.78rem;color:{THEME['text_muted']};">
        <a href="https://github.com/tanvigandhi1008/scripbox-seasonality-dashboard"
        target="_blank"
        style="color:{THEME['primary']};text-decoration:none;font-weight:500;">
        View source on GitHub
        </a>
        &nbsp;&nbsp;·&nbsp;&nbsp;
        Data sources: Yahoo Finance, FRED, AMFI India
        &nbsp;&nbsp;·&nbsp;&nbsp;
        Refreshed daily at 6:30 PM IST
    </div>
</div>
""", unsafe_allow_html=True)
