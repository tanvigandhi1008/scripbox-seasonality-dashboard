# ══════════════════════════════════════════════════════════════════════════════
# refresh/daily_refresh.py
# Runs daily via GitHub Actions at 13:00 UTC (6:30 PM IST).
# Pulls fresh data, recomputes all metrics, writes outputs to data/.
# FRED_API_KEY must be set as a GitHub Actions secret named FRED_API_KEY.
# ══════════════════════════════════════════════════════════════════════════════

import os
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from fredapi import Fred
from scipy import stats as scipy_stats

# ── PATHS ─────────────────────────────────────────────────────────────────────
# This file lives at repo_root/refresh/daily_refresh.py
# So Path(__file__).parents[1] = repo_root
REPO_ROOT      = Path(__file__).resolve().parents[1]
RAW_PATH       = REPO_ROOT / "data" / "raw"
PROCESSED_PATH = REPO_ROOT / "data" / "processed"
META_PATH      = REPO_ROOT / "data" / "metadata.csv"

# ── FRED API KEY ──────────────────────────────────────────────────────────────
# Read from environment variable set in GitHub Actions secrets.
# Never hardcode this in a public repository.
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
if not FRED_API_KEY:
    print("ERROR: FRED_API_KEY environment variable not set.")
    print("Add it as a GitHub Actions secret named FRED_API_KEY.")
    sys.exit(1)

fred   = Fred(api_key=FRED_API_KEY)
meta   = pd.read_csv(META_PATH)
today  = pd.Timestamp.today().strftime("%Y-%m-%d")
errors = []

IST = timezone(timedelta(hours=5, minutes=30))
print("=" * 65)
print(f"DAILY REFRESH — {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
print(f"Repo root: {REPO_ROOT}")
print("=" * 65)

# ── TICKER MAPS ───────────────────────────────────────────────────────────────

GLOBAL_EQUITY_TICKERS = {
    "S&P 500": "^GSPC", "Nasdaq Composite": "^IXIC", "Dow Jones": "^DJI",
    "MSCI World ETF": "URTH", "Euro Stoxx 50": "^STOXX50E",
    "FTSE 100": "^FTSE", "DAX": "^GDAXI", "CAC 40": "^FCHI",
    "Nikkei 225": "^N225", "Hang Seng": "^HSI", "ASX 200": "^AXJO",
    "SMI Switzerland": "^SSMI", "KOSPI South Korea": "^KS11",
    "Taiwan Weighted": "^TWII", "MSCI EM ETF": "EEM",
    "Shanghai Composite": "000001.SS", "Bovespa Brazil": "^BVSP",
    "IDX Composite": "^JKSE", "SET Thailand": "^SET.BK",
    "KLCI Malaysia": "^KLSE",
    "Energy": "XLE", "Financials": "XLF", "Technology": "XLK",
    "Healthcare": "XLV", "Industrials": "XLI", "Consumer Staples": "XLP",
    "Consumer Discretionary": "XLY", "Utilities": "XLU",
    "Real Estate": "XLRE", "Materials": "XLB",
    "Communication Services": "XLC",
    "S&P 500 Value": "IVE", "S&P 500 Growth": "IVW",
    "Momentum": "MTUM", "Low Volatility": "USMV", "Quality": "QUAL",
    "Small Cap Russell 2000": "IWM",
    "Semiconductor ETF": "SOXX", "Clean Energy ETF": "ICLN",
    "Global Real Estate ETF": "VNQI", "US Real Estate ETF": "VNQ",
    "Global Infrastructure ETF": "IGF", "Asia Pacific ETF": "VPL",
    "Frontier Markets ETF": "FM",
}

INDIAN_EQUITY_TICKERS = {
    "Nifty 50": "^NSEI", "Nifty Next 50": "^NSMIDCP",
    "Sensex": "^BSESN", "Nifty 500": "^CRSLDX", "Nifty 100": "^CNX100",
    "Nifty Midcap 150": "^NSEMDCP50",
    "Nifty Bank": "^NSEBANK", "Nifty IT": "^CNXIT",
    "Nifty Auto": "^CNXAUTO", "Nifty FMCG": "^CNXFMCG",
    "Nifty Pharma": "^CNXPHARMA", "Nifty Realty": "^CNXREALTY",
    "Nifty Metal": "^CNXMETAL", "Nifty Energy": "^CNXENERGY",
    "Nifty Infrastructure": "^CNXINFRA", "Nifty PSU Bank": "^CNXPSUBANK",
    "India VIX": "^INDIAVIX",
}

COMMODITY_TICKERS = {
    "Gold": "GC=F", "Silver": "SI=F",
    "Crude Oil WTI": "CL=F", "Crude Oil Brent": "BZ=F",
    "Natural Gas": "NG=F", "Copper": "HG=F",
    "Aluminium": "ALI=F", "Sugar": "SB=F",
    "Cotton": "CT=F", "Rice": "ZR=F",
    "Bloomberg Commodity ETF": "PDBC",
    "Diversified Commodity ETF": "DJP",
}

FX_TICKERS = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X", "USD/CHF": "CHF=X",
    "AUD/USD": "AUDUSD=X", "USD/CAD": "CAD=X",
    "NZD/USD": "NZDUSD=X", "USD/CNY": "CNY=X",
    "USD/INR": "INR=X", "USD/BRL": "BRL=X",
    "USD/ZAR": "ZAR=X", "USD/MXN": "MXN=X",
    "USD/TRY": "TRY=X", "USD/KRW": "KRW=X",
    "USD/IDR": "IDR=X", "USD/THB": "THB=X",
    "USD/SGD": "SGD=X",
    "EUR/INR": "EURINR=X", "GBP/INR": "GBPINR=X",
    "JPY/INR": "JPYINR=X", "AUD/INR": "AUDINR=X",
    "CHF/INR": "CHFINR=X",
    "DXY Dollar Index": "DX-Y.NYB",
}

# ── STEP 1: REFRESH YAHOO FINANCE FILES ───────────────────────────────────────
print("\n[1/5] Refreshing Yahoo Finance data...")

YF_FILE_TICKERS = {
    "global_equities.csv":  GLOBAL_EQUITY_TICKERS,
    "indian_equities.csv":  INDIAN_EQUITY_TICKERS,
    "commodities.csv":      COMMODITY_TICKERS,
    "fx_currencies.csv":    FX_TICKERS,
}

for fname, ticker_map in YF_FILE_TICKERS.items():
    fpath = RAW_PATH / fname
    if not fpath.exists():
        print(f"  SKIP {fname} — file not found in repo")
        errors.append(f"Missing raw file: {fname}")
        continue

    existing  = pd.read_csv(fpath, index_col=0, parse_dates=True)
    last_date = existing.index[-1]
    days_stale = (pd.Timestamp.today() - last_date).days

    if days_stale <= 1:
        print(f"  OK   {fname} — already current ({last_date.date()})")
        continue

    print(f"  Updating {fname} — last: {last_date.date()}, {days_stale} days stale")
    pull_start = (last_date - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    updated = skipped = 0

    for name, ticker in ticker_map.items():
        if name not in existing.columns:
            continue
        try:
            new_data = yf.download(
                ticker, start=pull_start, end=today,
                auto_adjust=True, progress=False
            )
            if new_data.empty:
                skipped += 1
                continue
            close = new_data["Close"].squeeze()
            existing[name] = existing[name].combine_first(close)
            updated += 1
        except Exception as e:
            errors.append(f"YF {fname}/{name}: {e}")
            skipped += 1

    existing.sort_index().to_csv(fpath)
    print(f"  {fname}: updated {updated} series, skipped {skipped}")

# ── STEP 2: REFRESH FRED DATA ─────────────────────────────────────────────────
print("\n[2/5] Refreshing FRED data...")

FRED_SERIES_MAP = {
    "US 3M T-Bill Yield":         "DTB3",
    "US 2Y Treasury Yield":       "DGS2",
    "US 5Y Treasury Yield":       "DGS5",
    "US 10Y Treasury Yield":      "DGS10",
    "US 30Y Treasury Yield":      "DGS30",
    "US 10Y minus 2Y Spread":     "T10Y2Y",
    "US 10Y minus 3M Spread":     "T10Y3M",
    "US IG Credit Spread OAS":    "BAMLC0A0CM",
    "US HY Credit Spread OAS":    "BAMLH0A0HYM2",
    "US 10Y Breakeven Inflation": "T10YIE",
    "US 5Y Breakeven Inflation":  "T5YIE",
    "Germany 10Y Bund Yield":     "IRLTLT01DEM156N",
    "UK 10Y Gilt Yield":          "IRLTLT01GBM156N",
    "Japan 10Y JGB Yield":        "IRLTLT01JPM156N",
    "France 10Y Yield":           "IRLTLT01FRM156N",
    "Italy 10Y Yield":            "IRLTLT01ITM156N",
    "India 10Y Government Bond":  "INDIRLTLT01STM",
    "US Federal Funds Rate":      "FEDFUNDS",
    "US 10Y Real Yield":          "DFII10",
    "India CPI Inflation":        "INDCPIALLMINMEI",
    "Zinc":                       "PZINCUSDM",
    "US GDP Growth Rate":         "A191RL1Q225SBEA",
    "India GDP Growth":           "INDGDPRQPSMEI",
    "US Unemployment Rate":       "UNRATE",
    "US CPI Inflation YoY":       "CPIAUCSL",
    # Baltic Dry Index: no valid free FRED series ID — excluded
    "US Industrial Production":   "INDPRO",
    "US Retail Sales":            "RSXFS",
    "US Housing Starts":          "HOUST",
    "US Consumer Confidence":     "UMCSENT",
    "US M2 Money Supply":         "M2SL",
    # US Bank Credit excluded from refresh (display-excluded series)
    "US Natural Gas Price":       "MHHNGSP",
}

fi_df   = pd.read_csv(RAW_PATH / "fixed_income.csv",    index_col=0, parse_dates=True)
vm_df   = pd.read_csv(RAW_PATH / "volatility_macro.csv", index_col=0, parse_dates=True)
comm_df = pd.read_csv(RAW_PATH / "commodities.csv",      index_col=0, parse_dates=True)

fred_updated = 0
for name, series_id in FRED_SERIES_MAP.items():
    try:
        new_data = fred.get_series(
            series_id,
            observation_start="2024-01-01",
            observation_end=today
        ).dropna()
        new_data.index = pd.to_datetime(new_data.index)
        if new_data.empty:
            continue
        if name in fi_df.columns:
            fi_df[name] = fi_df[name].combine_first(new_data)
        elif name in vm_df.columns:
            vm_df[name] = vm_df[name].combine_first(new_data)
        elif name in comm_df.columns:
            comm_df[name] = comm_df[name].combine_first(new_data)
        fred_updated += 1
    except Exception as e:
        errors.append(f"FRED {name}: {e}")

fi_df.sort_index().to_csv(RAW_PATH / "fixed_income.csv")
vm_df.sort_index().to_csv(RAW_PATH / "volatility_macro.csv")
comm_df.sort_index().to_csv(RAW_PATH / "commodities.csv")
print(f"  Updated {fred_updated} FRED series")

# ── STEP 3: REFRESH AMFI MUTUAL FUND DATA ─────────────────────────────────────
print("\n[3/5] Refreshing AMFI mutual fund data...")

MF_SCHEME_CODES = {
    "Large Cap Category":          119598,
    "Mid Cap Category":            119592,
    "Small Cap Category":          119574,
    "Flexi Cap Category":          119568,
    "Aggressive Hybrid Category":  119562,
    "Balanced Advantage Category": 119551,
    "Corporate Bond Category":     119545,
    "Liquid Category":             119513,
    "US Equity FOF Category":      120594,
}

mf_df = pd.read_csv(RAW_PATH / "indian_mf.csv", index_col=0, parse_dates=True)
mf_updated = 0

for name, code in MF_SCHEME_CODES.items():
    try:
        url  = f"https://api.mfapi.in/mf/{code}"
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            errors.append(f"AMFI {name}: HTTP {resp.status_code}")
            continue
        data = resp.json().get("data", [])
        if not data:
            continue
        df_mf = pd.DataFrame(data)
        df_mf["date"] = pd.to_datetime(df_mf["date"], format="%d-%m-%Y")
        df_mf = df_mf.set_index("date").sort_index()
        df_mf["nav"] = pd.to_numeric(df_mf["nav"], errors="coerce")
        if name in mf_df.columns:
            mf_df[name] = mf_df[name].combine_first(df_mf["nav"])
        else:
            mf_df[name] = df_mf["nav"]
        mf_updated += 1
    except Exception as e:
        errors.append(f"AMFI {name}: {e}")

mf_df.sort_index().to_csv(RAW_PATH / "indian_mf.csv")
print(f"  Updated {mf_updated} AMFI MF series")

# ── STEP 4: RECOMPUTE MONTHLY RETURNS ─────────────────────────────────────────
print("\n[4/5] Recomputing monthly returns...")

RAW_FILES = {}
for fname in ["global_equities.csv", "indian_equities.csv", "commodities.csv",
              "fx_currencies.csv", "fixed_income.csv", "indian_mf.csv",
              "volatility_macro.csv"]:
    fpath = RAW_PATH / fname
    if fpath.exists():
        RAW_FILES[fname] = pd.read_csv(fpath, index_col=0, parse_dates=True)

def compute_price_return(daily):
    return daily.resample("ME").last().pct_change(fill_method=None)

def compute_yield_change(daily):
    monthly = daily.resample("ME").last().ffill(limit=2)
    return monthly.diff() * 100

def compute_spread_change(daily):
    monthly = daily.resample("ME").last().ffill(limit=2)
    return monthly.diff() * 100

def compute_index_yoy(daily):
    monthly = daily.resample("ME").last().ffill(limit=3)
    return monthly.pct_change(periods=12)

def compute_rate_change(daily):
    monthly = daily.resample("ME").last().ffill(limit=3)
    return monthly.diff()

RETURN_FUNCTIONS = {
    "price":  compute_price_return,
    "yield":  compute_yield_change,
    "spread": compute_spread_change,
    "index":  compute_index_yoy,
    "rate":   compute_rate_change,
}

meta_lookup = meta.set_index("name").to_dict("index")
all_returns = {}

for _, row in meta.iterrows():
    name        = row["name"]
    fname       = row["file"]
    series_type = row["series_type"]
    df          = RAW_FILES.get(fname)
    if df is None or name not in df.columns:
        continue
    daily = df[name].dropna()
    if len(daily) < 24:
        continue
    func = RETURN_FUNCTIONS.get(series_type)
    if func is None:
        continue
    try:
        returns = func(daily).dropna()
        if len(returns) >= 12:
            all_returns[name] = returns
    except Exception as e:
        errors.append(f"Returns {name}: {e}")

monthly_returns = pd.DataFrame(all_returns)
monthly_returns.index = pd.to_datetime(monthly_returns.index)
monthly_returns = monthly_returns.sort_index()
monthly_returns = monthly_returns[monthly_returns.index >= "2000-01-01"]
monthly_returns.to_csv(PROCESSED_PATH / "monthly_returns.csv")
print(f"  monthly_returns.csv: {monthly_returns.shape[0]} rows x {monthly_returns.shape[1]} cols")

# ── STEP 5: INR RETURNS ────────────────────────────────────────────────────────
print("\n[5/5] Recomputing INR returns and seasonality stats...")

fx_raw   = RAW_FILES.get("fx_currencies.csv", pd.DataFrame())
usdinr_m = (
    fx_raw["USD/INR"].resample("ME").last().pct_change(fill_method=None)
    if "USD/INR" in fx_raw.columns else pd.Series(dtype=float)
)

inr_returns = monthly_returns.copy()
for _, row in meta.iterrows():
    name           = row["name"]
    convert_to_inr = str(row.get("convert_to_inr", "False")).strip().lower()
    if convert_to_inr not in ("true", "1", "yes"):
        continue
    if name not in monthly_returns.columns:
        continue
    local    = monthly_returns[name]
    combined = pd.concat([local, usdinr_m], axis=1, join="inner").dropna()
    combined.columns = ["local", "fx"]
    inr_returns[name] = (1 + combined["local"]) * (1 + combined["fx"]) - 1

inr_returns.to_csv(PROCESSED_PATH / "monthly_returns_inr.csv")
print(f"  monthly_returns_inr.csv: {inr_returns.shape}")

# ── SEASONALITY STATS ─────────────────────────────────────────────────────────

MONTH_NAMES = {
    1:"January", 2:"February",  3:"March",     4:"April",
    5:"May",     6:"June",      7:"July",       8:"August",
    9:"September",10:"October",11:"November",  12:"December"
}
MIN_OBS = 10

def build_stats(returns_df):
    all_rows = []
    for col in returns_df.columns:
        m_info = meta_lookup.get(col, {})
        for month_num in range(1, 13):
            clean = returns_df[col].dropna()
            clean = clean[clean.index.month == month_num]
            n_obs = len(clean)
            row = {
                "series_name":   col,
                "month":         month_num,
                "month_name":    MONTH_NAMES[month_num],
                "n_obs":         n_obs,
                "asset_class":   m_info.get("asset_class", ""),
                "sub_class":     m_info.get("sub_class", ""),
                "geography":     m_info.get("geography", ""),
                "currency":      m_info.get("currency", ""),
                "series_type":   m_info.get("series_type", ""),
                "avg_return":    round(float(clean.mean()),    6) if n_obs >= MIN_OBS else np.nan,
                "median_return": round(float(clean.median()),  6) if n_obs >= MIN_OBS else np.nan,
                "std_return":    round(float(clean.std()),     6) if n_obs >= MIN_OBS else np.nan,
                "win_rate":      round(float((clean > 0).mean()), 4) if n_obs >= MIN_OBS else np.nan,
                "best_return":   round(float(clean.max()),    6) if n_obs >= MIN_OBS else np.nan,
                "worst_return":  round(float(clean.min()),    6) if n_obs >= MIN_OBS else np.nan,
                "best_year":     int(clean.idxmax().year)        if n_obs >= MIN_OBS else np.nan,
                "worst_year":    int(clean.idxmin().year)        if n_obs >= MIN_OBS else np.nan,
                "t_stat":        np.nan,
                "p_value":       np.nan,
            }
            if n_obs >= 3:
                t, p = scipy_stats.ttest_1samp(clean, popmean=0)
                row["t_stat"]  = round(float(t), 4)
                row["p_value"] = round(float(p), 4)
            all_rows.append(row)
    return pd.DataFrame(all_rows)

stats_local = build_stats(monthly_returns)
stats_inr   = build_stats(inr_returns)

stats_local.to_csv(PROCESSED_PATH / "seasonality_stats.csv",     index=False)
stats_inr.to_csv(  PROCESSED_PATH / "seasonality_stats_inr.csv", index=False)
print(f"  seasonality_stats.csv: {len(stats_local)} rows")

# ── REGIME LABELS ─────────────────────────────────────────────────────────────

fed_r    = monthly_returns.get("US Federal Funds Rate",  pd.Series(dtype=float)).dropna()
usdinr_r = monthly_returns.get("USD/INR",                pd.Series(dtype=float)).dropna()
nifty_r  = monthly_returns.get("Nifty 50",               pd.Series(dtype=float)).dropna()
vix_raw  = RAW_FILES.get("volatility_macro.csv", pd.DataFrame())
vix_lvl  = (
    vix_raw["VIX US Equity Volatility"].resample("ME").last()
    if "VIX US Equity Volatility" in vix_raw.columns else pd.Series(dtype=float)
)

def rate_regime(x):
    return "Rising" if x > 0 else ("Falling" if x < 0 else "Neutral")

def rupee_regime(x):
    return "Weak Rupee" if x > 0.005 else ("Strong Rupee" if x < -0.005 else "Stable Rupee")

def equity_regime(x):
    return "Unknown" if pd.isna(x) else ("Bull" if x > 0.05 else ("Bear" if x < -0.05 else "Neutral"))

def risk_regime(x):
    return "Unknown" if pd.isna(x) else ("Risk-Off" if x > 25 else ("Risk-On" if x < 15 else "Neutral"))

nifty_3m  = (1 + nifty_r).rolling(3).apply(lambda x: x.prod()) - 1
regime_df = pd.DataFrame({
    "rate_regime":   fed_r.apply(rate_regime),
    "rupee_regime":  usdinr_r.apply(rupee_regime),
    "equity_regime": nifty_3m.apply(equity_regime),
    "risk_regime":   vix_lvl.apply(risk_regime),
}).sort_index()
regime_df.to_csv(PROCESSED_PATH / "regime_labels.csv")
print(f"  regime_labels.csv: {len(regime_df)} months")

# ── WRITE REFRESH LOG ─────────────────────────────────────────────────────────
# The dashboard reads this to display "Last updated" on every page.

log = {
    "last_updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "last_updated_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
    "errors": errors,
    "series_count": int(monthly_returns.shape[1]),
    "months_count":  int(monthly_returns.shape[0]),
}
with open(PROCESSED_PATH / "refresh_log.json", "w") as f:
    json.dump(log, f, indent=2)

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("REFRESH COMPLETE")
print("=" * 65)
print(f"  Completed at : {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
print(f"  Monthly returns : {monthly_returns.shape}")
print(f"  Seasonality stats : {len(stats_local)} rows")
print(f"  Regime labels : {len(regime_df)} months")
if errors:
    print(f"\n  Errors ({len(errors)}):")
    for e in errors:
        print(f"    {e}")
    # Only fail the run if more than 3 errors — single transient API
    # failures (e.g. FRED internal server error) should not fail the whole run
    if len(errors) > 3:
        sys.exit(1)
else:
    print("\n  No errors.")
print("\nDone.")
