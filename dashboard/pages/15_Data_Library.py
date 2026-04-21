
# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 15_Data_Library.py
# PURPOSE: Full series catalogue, data sources, gap disclosures, methodology
#          explanations, and Google Drive data file access.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st


from utils.data_loader import (
    load_metadata, render_sidebar, inject_css,
    filter_by_market_scope, THEME
)
import pandas as pd

st.set_page_config(
    page_title="Data Library · Scripbox Seasonality",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
render_sidebar()

scope = st.session_state.get("market_scope", "Domestic")

meta_all = load_metadata()
meta     = filter_by_market_scope(meta_all, scope)

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown('''<div class="page-title">Data Library</div>''',
            unsafe_allow_html=True)
st.markdown(
    f'''<div class="page-subtitle">
    Methodology, series catalogue, data sources, and file access ·
    {scope} scope · {len(meta)} series visible
    </div>''',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 1: METHODOLOGY ────────────────────────────────────────────────────
st.markdown('''<div class="section-header">How Every Metric is Calculated</div>''',
            unsafe_allow_html=True)

st.markdown(
    '''<div class="info-card">
    Every number on this dashboard traces back to a specific calculation.
    This section explains each metric in plain language so any user can
    verify or explain the numbers independently.
    </div>''',
    unsafe_allow_html=True
)

with st.expander("Monthly Return — how it is computed"):
    st.markdown("""
**Definition:** The percentage change in price from the last trading day
of one month to the last trading day of the next month.

**Formula:** Monthly Return = (Price at end of month T ÷ Price at end of
month T-1) − 1

**Example:** If Nifty 50 closed at 22,000 in January and 22,500 in
February, the February return = (22,500 ÷ 22,000) − 1 = 0.0227 = +2.27%

**Storage:** Values are stored as decimals in monthly_returns.csv.
So 0.0227 represents +2.27%. The dashboard multiplies by 100 for display.

**For yield series (bond yields, credit spreads):** Monthly change is
computed as the absolute difference between month-end levels, not
percentage change. Example: if the US 10Y yield was 4.00% in January
and 4.20% in February, the change is +0.20 percentage points = +20 basis
points. These are stored as diff() × 100 in the stats CSV, giving values
already in basis points (e.g. 20, not 0.0020).

**For index series (CPI, GDP):** Year-over-year percentage change,
computed as (value this month ÷ value 12 months ago) − 1.

**Source data:** Daily closing prices from Yahoo Finance (equities,
commodities, FX), FRED (yields, macro), and AMFI India (mutual funds).
""")

with st.expander("Average Return — how it is computed"):
    st.markdown("""
**Definition:** The arithmetic mean of all monthly returns for that
series in that calendar month across all available years.

**Formula:** Average Return = Sum of all January returns ÷ Number of
Januaries in dataset

**Example:** If Nifty 50 had January returns of +3%, -1%, +5%, +2%
across four years, the average January return = (3 − 1 + 5 + 2) ÷ 4
= +2.25%

**Minimum observations:** A minimum of 10 years of data is required
before a monthly average is computed. With fewer observations, the cell
shows NaN (blank).

**Limitation:** Arithmetic mean is influenced by extreme outliers.
One very large or very negative year can pull the average significantly.
Use Median Return alongside Average Return for a fuller picture.
""")

with st.expander("Median Return — how it is computed"):
    st.markdown("""
**Definition:** The middle value when all monthly returns for that series
in that calendar month are sorted from lowest to highest.

**Example:** If Nifty 50 had January returns of -5%, +1%, +3%, +4%, +7%
across five years, sorted: -5, +1, +3, +4, +7. The middle value is +3%.
Median = +3%.

**Why use median?** The median is not affected by extreme outliers.
A single crash year (like March 2020) or a single boom year will not
distort the median the way it distorts the average. The median tells
you what a typical year looked like.

**When to trust median over average:** If average and median are close,
the return distribution is fairly symmetric. If they diverge significantly,
there are outlier years pulling the average away from the typical
experience. In that case, median is a more reliable measure of what
an investor would typically have experienced.
""")

with st.expander("Win Rate — how it is computed"):
    st.markdown("""
**Definition:** The proportion of years in which the monthly return was
positive (greater than zero).

**Formula:** Win Rate = Number of years with positive return in that
month ÷ Total number of years with data in that month

**Example:** If Nifty 50 had positive January returns in 17 out of 25
years, Win Rate = 17 ÷ 25 = 0.68 = 68%

**How to use it:** Win rate combined with average return gives stronger
conviction about a seasonal pattern:
- High win rate + positive average = strong seasonal tailwind
- Low win rate + positive average = average driven by a few large years
- High win rate + negative average = consistently weak month

A win rate above 65% with a positive average return is a good signal of
a reliable seasonal pattern.
""")

with st.expander("Statistical Significance (p-value) — how it is computed"):
    st.markdown("""
**Definition:** The p-value tests whether the observed seasonal pattern
could have occurred by random chance.

**Method:** We use a one-sample t-test to test whether the mean monthly
return is significantly different from zero. The test assumes the monthly
returns are approximately normally distributed.

**Formula:** t-statistic = Mean return ÷ (Standard deviation ÷ √n)
where n = number of observations. The p-value is derived from this
t-statistic using the t-distribution with n-1 degrees of freedom.

**How to interpret:**
- p-value < 0.05: less than 5% probability the pattern is random.
  Strong evidence of a genuine seasonal tendency.
- p-value < 0.10: less than 10% probability. Moderate evidence.
- p-value > 0.20: pattern may well be random noise.

**Important caveat:** With only 25 years of monthly data (25 observations
per month), statistical power is limited. Very low p-values are rare.
A threshold of p < 0.10 is reasonable for monthly seasonality data.
Do not require p < 0.05 as a strict cutoff — it will filter out many
genuine patterns.
""")

with st.expander("Consistency Score — how it is computed"):
    st.markdown("""
**Definition:** A composite score from 0 to 1 that combines three
measures of pattern reliability into a single number.

**Formula:**
Consistency Score = (Win Rate × 0.40) + (Normalised Magnitude × 0.40)
                  + ((1 − p-value) × 0.20)

**Components:**
- Win Rate (40% weight): How often the pattern repeats.
  A win rate of 0.70 contributes 0.70 × 0.40 = 0.28 to the score.
- Normalised Magnitude (40% weight): How large the return is, expressed
  as a fraction of the 95th percentile return in the dataset (to avoid
  extreme outliers dominating). Clipped between 0 and 1.
- Statistical Significance (20% weight): 1 minus the p-value.
  A p-value of 0.05 contributes (1 − 0.05) × 0.20 = 0.19 to the score.

**Interpretation:**
- Score ≥ 0.65: Strong, reliable, statistically supported pattern
- Score 0.45–0.65: Moderate pattern, worth monitoring
- Score < 0.45: Weak pattern, may be random

**Example:** A series with win rate = 0.72, normalised magnitude = 0.60,
p-value = 0.08 would score:
(0.72 × 0.40) + (0.60 × 0.40) + (0.92 × 0.20) = 0.288 + 0.240 + 0.184
= 0.712 — a strong pattern.
""")

with st.expander("INR Conversion — how it is computed"):
    st.markdown("""
**Definition:** When Currency View is set to INR, returns for
internationally-priced series are converted to rupee terms.

**Formula:** INR Return = (1 + Local Currency Return) × (1 + USD/INR
Return) − 1

**Example:** If the S&P 500 returned +3% in USD in January, and USD/INR
also rose by +1% (rupee weakened), then the INR return =
(1.03 × 1.01) − 1 = 0.0403 = +4.03%

**Why this matters:** An Indian investor who invested via LRS in a US ETF
earns the combined return of the US market move and the rupee movement.
When the rupee weakens, international investments gain extra return in
INR terms. When the rupee strengthens, the INR return is lower than
the local currency return.

**What stays the same in INR view:** Domestic series (Nifty 50, Indian
sector indices, MCX commodities in INR, USD/INR itself) are already in
rupee terms so their values do not change between Local Currency and INR
views. Only series with convert_to_inr = True in metadata are converted.

**FX series:** Exchange rate pairs are never converted to INR because
an exchange rate is already a ratio between two currencies. Converting
it to INR would produce a meaningless number.
""")

with st.expander("Regime Classification — how regimes are assigned"):
    st.markdown("""
**Definition:** Each month in the dataset is classified into a macro
regime across four dimensions based on that month's data.

**Rate Regime** (based on US Federal Funds Rate monthly change):
- Rising: Fed Funds Rate increased that month
- Falling: Fed Funds Rate decreased that month
- Neutral: Fed Funds Rate unchanged

**Rupee Regime** (based on USD/INR monthly return):
- Weak Rupee: USD/INR rose by more than 0.5% (rupee weakened)
- Strong Rupee: USD/INR fell by more than 0.5% (rupee strengthened)
- Stable Rupee: movement within ±0.5%

**Equity Regime** (based on Nifty 50 trailing 3-month return):
- Bull: trailing 3-month return above +5%
- Bear: trailing 3-month return below -5%
- Neutral: between -5% and +5%

**Risk Regime** (based on VIX US Equity Volatility end-of-month level):
- Risk-Off: VIX above 25
- Risk-On: VIX below 15
- Neutral: VIX between 15 and 25

**How regime analysis works:** When a regime filter is selected on the
Regime Analysis or Pattern Screener pages, only months matching that
regime classification are used to compute the seasonal statistics.
This surfaces patterns that are specific to the current macro environment
rather than averaged across all historical conditions.

**Caveat:** Regime labels are based on trailing data and simple
thresholds. They are a useful analytical framework, not a precise
economic measurement. Interpret regime-filtered results with awareness
that fewer observations means higher statistical uncertainty.
""")

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 2: DATA FILE DOWNLOADS ───────────────────────────────────────────
st.markdown('''<div class="section-header">Download the Data Files</div>''',
            unsafe_allow_html=True)

st.markdown(
    '''<div class="info-card">
    Download any CSV file directly from this page. These are the same files
    the dashboard reads from. Raw files contain original price and yield
    series. Processed files contain computed monthly returns and seasonality
    statistics.
    </div>''',
    unsafe_allow_html=True
)

from utils.data_loader import BASE, PROCESSED, RAW

_DOWNLOAD_FILES = {
    "Processed Data": [
        ("Monthly Returns (Local Currency)",  f"{PROCESSED}/monthly_returns.csv"),
        ("Monthly Returns (INR)",              f"{PROCESSED}/monthly_returns_inr.csv"),
        ("Seasonality Stats (Local Currency)", f"{PROCESSED}/seasonality_stats.csv"),
        ("Seasonality Stats (INR)",            f"{PROCESSED}/seasonality_stats_inr.csv"),
        ("Regime Labels",                      f"{PROCESSED}/regime_labels.csv"),
    ],
    "Raw Data": [
        ("Global Equities",   f"{RAW}/global_equities.csv"),
        ("Indian Equities",   f"{RAW}/indian_equities.csv"),
        ("Commodities",       f"{RAW}/commodities.csv"),
        ("FX Currencies",     f"{RAW}/fx_currencies.csv"),
        ("Fixed Income",      f"{RAW}/fixed_income.csv"),
        ("Indian Mutual Funds", f"{RAW}/indian_mf.csv"),
        ("Volatility & Macro",  f"{RAW}/volatility_macro.csv"),
    ],
    "Metadata": [
        ("Series Metadata",   f"{BASE}/data/metadata.csv"),
    ],
}

import os as _os
for section_label, file_list in _DOWNLOAD_FILES.items():
    st.markdown(
        f'''<div style="font-weight:600;font-size:0.88rem;
        color:{THEME["text_secondary"]};margin:1rem 0 0.4rem 0;
        text-transform:uppercase;letter-spacing:0.05em;">
        {section_label}</div>''',
        unsafe_allow_html=True
    )
    cols = st.columns(3)
    for i, (label, fpath) in enumerate(file_list):
        with cols[i % 3]:
            if _os.path.exists(fpath):
                with open(fpath, "rb") as _f:
                    st.download_button(
                        label=f"Download {label}",
                        data=_f.read(),
                        file_name=_os.path.basename(fpath),
                        mime="text/csv",
                        use_container_width=True,
                    )
            else:
                st.markdown(
                    f'''<div style="font-size:0.8rem;
                    color:{THEME["text_muted"]};padding:0.4rem 0;">
                    {label} — not available</div>''',
                    unsafe_allow_html=True
                )

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 3: DATA SOURCES ───────────────────────────────────────────────────
st.markdown('''<div class="section-header">Data Sources</div>''',
            unsafe_allow_html=True)

sources = [
    {
        "source":    "Yahoo Finance (yfinance)",
        "covers":    "Global and Indian equities, commodities, FX, volatility indices",
        "frequency": "Daily — aggregated to monthly",
        "start":     "January 2000 where available",
        "notes":     "Free API. Some NSE indices blocked from cloud IPs — flagged in series notes.",
    },
    {
        "source":    "FRED (Federal Reserve Economic Data)",
        "covers":    "US Treasury yields, credit spreads, inflation expectations, macro indicators, Zinc prices",
        "frequency": "Daily or monthly depending on series",
        "start":     "January 2000 where available",
        "notes":     "Free API. FRED API key required — stored in notebook Cell 2.",
    },
    {
        "source":    "AMFI India (mfapi.in)",
        "covers":    "Indian mutual fund category NAV data",
        "frequency": "Daily — aggregated to monthly",
        "start":     "January 2000 where available",
        "notes":     "Free public API. Category averages computed across all funds in each SEBI category.",
    },
    {
        "source":    "ExchangeRate-API",
        "covers":    "USD/INR and other INR cross rates for currency conversion",
        "frequency": "Daily",
        "start":     "January 2000 where available",
        "notes":     "Used to convert local currency returns to INR terms.",
    },
]

for src in sources:
    with st.expander(src["source"]):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Covers:** {src['covers']}")
            st.markdown(f"**Frequency:** {src['frequency']}")
        with c2:
            st.markdown(f"**History start:** {src['start']}")
            st.markdown(f"**Notes:** {src['notes']}")

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 4: DOCUMENTED DATA GAPS ──────────────────────────────────────────
st.markdown('''<div class="section-header">Documented Data Gaps</div>''',
            unsafe_allow_html=True)

st.markdown(
    '''<div class="info-card">
    Every data gap is disclosed explicitly. No series was silently excluded
    or replaced without documentation.
    </div>''',
    unsafe_allow_html=True
)

GAPS = [
    {
        "series":   "MCX Gold, Silver, Crude Oil, Natural Gas, Copper, Zinc, Aluminium (INR Synthetic)",
        "gap":      "Direct MCX price data not available via free APIs",
        "approach": "Constructed synthetically using international USD spot prices converted to INR using USD/INR exchange rates. Labelled explicitly as synthetic throughout the dashboard.",
        "impact":   "Low — synthetic series closely tracks actual MCX prices. Divergence may arise from exchange rate timing differences.",
    },
    {
        "series":   "JSE South Africa",
        "gap":      "Yahoo Finance ticker ^J200 not returning data",
        "approach": "Excluded from dataset. Documented gap.",
        "impact":   "Low — South Africa is a minor allocation for Indian investors.",
    },
    {
        "series":   "Lead and Nickel futures (LME)",
        "gap":      "LME Lead and Nickel not available on Yahoo Finance",
        "approach": "Excluded. Zinc and Aluminium cover base metal exposure.",
        "impact":   "Low.",
    },
    {
        "series":   "Zinc (original Yahoo Finance ticker ZNC=F)",
        "gap":      "ZNC=F returned stale price of $2,297 for 75 months from February 2020",
        "approach": "Replaced with FRED series PZINCUSDM (IMF LME Zinc price). Verified and corrected.",
        "impact":   "Fixed — Zinc data is now accurate from FRED.",
    },
    {
        "series":   "India CPI Inflation (original)",
        "gap":      "Was accidentally pulling US CPI (CPIAUCSL) instead of India CPI",
        "approach": "Replaced with correct FRED series INDCPIALLMINMEI. Verified and corrected.",
        "impact":   "Fixed — India CPI data now reflects actual Indian inflation.",
    },
    {
        "series":   "India Industrial Production",
        "gap":      "FRED series INDPROINDMISMEI stopped at January 2023",
        "approach": "Series retained with data up to January 2023. No free alternative source available. Gap documented.",
        "impact":   "Medium — IIP data is stale. Stats are valid for available history (2001-2023).",
    },
    {
        "series":   "Frontier Markets ETF (FM)",
        "gap":      "Yahoo Finance stopped returning recent data after January 2025",
        "approach": "Series retained with data up to January 2025. Documented gap.",
        "impact":   "Low — Frontier markets is a minor allocation.",
    },
    {
        "series":   "Aggressive Hybrid Category (Mutual Fund)",
        "gap":      "Three months had NAV restatement outliers of 900-1836% returns",
        "approach": "Outlier values clipped. Stats recomputed on cleaned data.",
        "impact":   "Fixed — category averages now reflect normal return patterns.",
    },
]

for gap in GAPS:
    with st.expander(gap["series"]):
        st.markdown(f"**Gap:** {gap['gap']}")
        st.markdown(f"**Approach taken:** {gap['approach']}")
        st.markdown(f"**Impact on analysis:** {gap['impact']}")

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 5: FULL SERIES CATALOGUE ─────────────────────────────────────────
st.markdown('''<div class="section-header">Full Series Catalogue</div>''',
            unsafe_allow_html=True)

col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    cat_ac = st.selectbox(
        "Asset Class",
        ["All"] + sorted(meta["asset_class"].unique().tolist()),
        key="cat_ac"
    )
with col_f2:
    cat_inv = st.selectbox(
        "Investability",
        ["All", "domestic", "international", "international_etf", "benchmark"],
        key="cat_inv"
    )
with col_f3:
    cat_geo = st.selectbox(
        "Geography",
        ["All"] + sorted(meta["geography"].dropna().unique().tolist()),
        key="cat_geo"
    )
with col_f4:
    cat_search = st.text_input(
        "Search by name", key="cat_search",
        placeholder="e.g. Nifty, Gold, Treasury"
    )

cat_df = meta.copy()
if cat_ac  != "All":
    cat_df = cat_df[cat_df["asset_class"]   == cat_ac]
if cat_inv != "All":
    cat_df = cat_df[cat_df["investability"] == cat_inv]
if cat_geo != "All":
    cat_df = cat_df[cat_df["geography"]     == cat_geo]
if cat_search.strip():
    cat_df = cat_df[
        cat_df["name"].str.contains(cat_search.strip(), case=False, na=False)
    ]

display_cat = cat_df[[
    "name", "asset_class", "sub_class", "geography",
    "currency", "investability", "series_type", "notes"
]].copy()
display_cat.columns = [
    "Series Name", "Asset Class", "Sub-class", "Geography",
    "Currency", "Investability", "Series Type", "Notes"
]
display_cat["Notes"] = display_cat["Notes"].fillna("")

st.markdown(
    f'''<p style="font-size:0.85rem;color:{THEME["text_secondary"]};">
    Showing <strong>{len(display_cat)}</strong> of
    <strong>{len(meta)}</strong> series in {scope} scope
    </p>''',
    unsafe_allow_html=True
)

st.dataframe(display_cat, use_container_width=True, hide_index=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── SECTION 6: INVESTABILITY CLASSIFICATION ───────────────────────────────────
st.markdown('''<div class="section-header">Investability Classification</div>''',
            unsafe_allow_html=True)

inv_explanations = {
    "domestic": (
        "Indian market series directly investable through Indian brokers, "
        "mutual funds, or exchanges. Includes Nifty indices, Indian sector "
        "indices, India 10Y bond, MCX commodities in INR, USD/INR, and "
        "Indian MF categories."
    ),
    "international": (
        "International markets accessible to Indian investors through the "
        "Liberalised Remittance Scheme (LRS) via a foreign brokerage. "
        "Includes major FX pairs, international commodity spot prices, and "
        "select global markets."
    ),
    "international_etf": (
        "US-listed or global ETFs accessible through LRS via a foreign "
        "brokerage or through Indian AMC international fund-of-funds. "
        "Includes sector ETFs, factor ETFs, bond ETFs, and global index ETFs."
    ),
    "benchmark": (
        "Reference indices and macro indicators not directly investable "
        "but tracked as standard benchmarks. Includes S&P 500, Nikkei 225, "
        "US Treasury yields, credit spreads, and macro series. Shown in "
        "both Domestic and Global scope, labelled [Ref] in heatmaps."
    ),
}

cols_inv = st.columns(2)
for i, (inv_type, explanation) in enumerate(inv_explanations.items()):
    with cols_inv[i % 2]:
        count = len(meta[meta["investability"] == inv_type])
        st.markdown(
            f'''<div style="background:{THEME["surface"]};
            border:1px solid {THEME["border"]};
            border-left:4px solid {THEME["primary"]};
            border-radius:8px;padding:1rem;margin-bottom:0.75rem;">
            <div style="font-weight:700;font-size:0.9rem;margin-bottom:0.3rem;">
            {inv_type}
            <span style="font-weight:400;font-size:0.8rem;
            color:{THEME["text_muted"]};margin-left:8px;">
            {count} series in {scope} scope</span>
            </div>
            <div style="font-size:0.82rem;color:{THEME["text_secondary"]};">
            {explanation}
            </div></div>''',
            unsafe_allow_html=True
        )
