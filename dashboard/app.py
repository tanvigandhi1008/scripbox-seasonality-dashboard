import streamlit as st
from utils.data_loader import inject_css, render_sidebar, THEME, load_metadata
import json
from pathlib import Path

st.set_page_config(
    page_title="Scripbox Global Seasonality Dashboard",
    page_icon="\U0001f4c5",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
render_sidebar()

try:
    meta         = load_metadata()
    series_count = len(meta)
    years_note   = "25 years of data"
except Exception:
    series_count = 160
    years_note   = "25 years of data"

# Read last updated timestamp from refresh log if available
last_updated = "Updated daily"
try:
    from utils.data_loader import PROCESSED
    log_path = Path(PROCESSED) / "refresh_log.json"
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
        last_updated = log.get("last_updated_ist", last_updated)
except Exception:
    pass

st.markdown('''
<div style="text-align:center; padding: 4rem 2rem 2rem 2rem;">
    <div style="font-size:2rem; font-weight:700; color:#1A1A2E; margin-bottom:0.5rem;">
        Global Seasonality Dashboard
    </div>
    <div style="font-size:1rem; color:#6B748A; margin-bottom:2rem;">
        Recurring seasonal patterns across global and Indian asset classes
    </div>
</div>
''', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
<div style="background:{THEME['surface']};border:1px solid {THEME['border']};
border-left:4px solid {THEME['primary']};border-radius:10px;padding:1.2rem;">
<div style="font-weight:600;margin-bottom:0.4rem;">Use the sidebar to navigate</div>
<div style="font-size:0.85rem;color:{THEME['text_secondary']};">
Select Market Scope, Currency View, and other filters.
Settings apply across all pages automatically.
</div>
</div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
<div style="background:{THEME['surface']};border:1px solid {THEME['border']};
border-left:4px solid {THEME['primary']};border-radius:10px;padding:1.2rem;">
<div style="font-weight:600;margin-bottom:0.4rem;">Domestic vs Global scope</div>
<div style="font-size:0.85rem;color:{THEME['text_secondary']};">
Domestic shows Indian markets and global benchmarks.
Global adds LRS and FoF-accessible international assets.
</div>
</div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
<div style="background:{THEME['surface']};border:1px solid {THEME['border']};
border-left:4px solid {THEME['primary']};border-radius:10px;padding:1.2rem;">
<div style="font-weight:600;margin-bottom:0.4rem;">{series_count} series, {years_note}</div>
<div style="font-size:0.85rem;color:{THEME['text_secondary']};">
Covering equities, fixed income, commodities, currencies,
mutual funds, volatility, and macro indicators.
</div>
</div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align:center;font-size:0.8rem;color:{THEME['text_muted']};
padding:2rem 0 1rem 0;">
{last_updated} · Sources: Yahoo Finance, FRED, AMFI India
</div>""", unsafe_allow_html=True)
