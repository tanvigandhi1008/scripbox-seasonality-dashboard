import streamlit as st
from utils.data_loader import inject_css, render_sidebar, THEME, load_metadata
import json
from pathlib import Path

st.set_page_config(
    page_title="Seasonality Dashboard",
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

LOGO_B64 = "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"

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex; justify-content:space-between;
align-items:flex-start; padding:1.5rem 0 0 0;">
    <div style="flex:1;">
        <div style="font-size:2rem;font-weight:700;
        color:{THEME['text_primary']};margin-bottom:0.3rem;">
            Seasonality Dashboard
        </div>
        <div style="font-size:0.95rem;color:{THEME['text_secondary']};
        margin-bottom:0.5rem;">
            Recurring seasonal patterns across global and Indian asset classes
        </div>
        <div style="display:inline-block;
        background:{THEME['primary_light']};
        border:1px solid {THEME['primary_mid']};
        border-radius:20px;
        padding:0.25rem 0.9rem;
        font-size:0.8rem;
        color:{THEME['primary']};
        font-weight:600;">
            Data as of {last_updated_ist}
        </div>
    </div>
    <div style="flex-shrink:0;margin-left:2rem;padding-top:0.2rem;">
        <img src="data:image/png;base64,{LOGO_B64}"
             style="height:44px;"
             alt="Scripbox">
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr style='margin:1rem 0;'>", unsafe_allow_html=True)

# ── ABOUT ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:{THEME['surface']};
border:1px solid {THEME['border']};
border-left:4px solid {THEME['primary']};
border-radius:10px;
padding:1.4rem 1.8rem;
margin-bottom:1.2rem;">
<div style="font-size:1rem;font-weight:700;
color:{THEME['text_primary']};margin-bottom:0.6rem;">
About this Dashboard
</div>
<div style="font-size:0.875rem;color:{THEME['text_secondary']};line-height:1.75;">
Seasonality refers to the tendency of financial markets to behave differently
depending on the time of year. January might historically be strong for equities.
October might tend to be weak for gold. These patterns do not repeat perfectly
every year, but they repeat often enough and consistently enough to be worth
knowing about. One of the most important questions in asset allocation is not
just what to invest in, but when conditions tend to favour certain asset classes
over others.
<br><br>
This dashboard is built to make those patterns visible, measurable, and
actionable. It covers {series_count} asset series spanning Indian and global
equities, fixed income, commodities, currencies, mutual fund categories,
volatility indices, and macroeconomic indicators, all going back to January 2000
where data is available. For every series and every calendar month, the dashboard
computes the average return, median return, win rate, and statistical
significance, so that genuine patterns can be distinguished from noise.
<br><br>
Beyond calendar patterns, the dashboard also looks at how different macro
environments affect returns — whether interest rates are rising or falling,
whether the rupee is strengthening or weakening, whether equity markets are in
a bull or bear phase. This makes it possible to filter patterns by the conditions
that most closely resemble today, and ask questions like: which months have
historically been strong for Nifty 50? Does gold tend to do well in a weak
rupee environment? How do Indian equities behave in rate-rising regimes? What
does the current macro regime imply for asset allocation over the next few
months? These are not questions that can be answered quickly with standard
market data tools. This dashboard was built specifically to surface them in one
place, updated automatically every day.
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
border-left:4px solid {THEME['primary']};border-radius:10px;padding:1.1rem;">
<div style="font-weight:600;font-size:0.9rem;margin-bottom:0.3rem;">
Use the sidebar to navigate</div>
<div style="font-size:0.83rem;color:{THEME['text_secondary']};">
Select Market Scope, Currency View, Lookback Window, and Significance
Filter. All settings apply across every page automatically.
</div></div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
<div style="background:{THEME['surface']};border:1px solid {THEME['border']};
border-left:4px solid {THEME['primary']};border-radius:10px;padding:1.1rem;">
<div style="font-weight:600;font-size:0.9rem;margin-bottom:0.3rem;">
Domestic vs Global scope</div>
<div style="font-size:0.83rem;color:{THEME['text_secondary']};">
Domestic shows Indian markets and global reference benchmarks.
Global adds all LRS and FoF-accessible international assets.
</div></div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
<div style="background:{THEME['surface']};border:1px solid {THEME['border']};
border-left:4px solid {THEME['primary']};border-radius:10px;padding:1.1rem;">
<div style="font-weight:600;font-size:0.9rem;margin-bottom:0.3rem;">
Interpreting the heatmaps</div>
<div style="font-size:0.83rem;color:{THEME['text_secondary']};">
Green cells indicate historically positive months. Red cells indicate
weak months. Use the significance filter to show only statistically
reliable patterns.
</div></div>""", unsafe_allow_html=True)

st.markdown("<hr style='margin:1rem 0;'>", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;padding:1rem 0 0.5rem 0;">
    <div style="font-size:0.82rem;color:{THEME['text_muted']};margin-bottom:0.3rem;">
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
