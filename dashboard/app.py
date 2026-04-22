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
align-items:flex-start; padding:0.2rem 0 0 0;">
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
             style="height:80px;"
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
