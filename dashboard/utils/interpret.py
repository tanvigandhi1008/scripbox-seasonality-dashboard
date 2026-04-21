import pandas as pd
import numpy as np

MONTH_FULL = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
              7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}

def interpret_series_month(name, month, avg_return, win_rate, p_value, n_obs,
                            best_return=None, best_year=None,
                            worst_return=None, worst_year=None,
                            consistency_score=None):
    """
    Generate a plain English one-paragraph interpretation of a seasonal pattern
    for a given series and month. Suitable for display below any chart.
    """
    if any(pd.isna(v) for v in [avg_return, win_rate, p_value, n_obs]):
        return "Insufficient data to interpret this pattern."

    month_name  = MONTH_FULL.get(int(month), str(month))
    direction   = "positive" if avg_return >= 0 else "negative"
    sign        = "+" if avg_return >= 0 else ""
    ret_str     = f"{sign}{avg_return*100:.2f}%"
    wr_str      = f"{win_rate*100:.0f}%"
    n_str       = str(int(n_obs))

    # Significance language
    if p_value < 0.01:
        sig_str = "highly statistically significant (p < 0.01), meaning this is very unlikely to be random noise"
    elif p_value < 0.05:
        sig_str = "statistically significant (p < 0.05)"
    elif p_value < 0.10:
        sig_str = "marginally significant (p < 0.10) -- treat with some caution"
    else:
        sig_str = f"not statistically significant (p = {p_value:.2f}) -- this pattern may be noise"

    # Win rate language
    if win_rate >= 0.75:
        wr_desc = "very consistently"
    elif win_rate >= 0.60:
        wr_desc = "more often than not"
    elif win_rate >= 0.50:
        wr_desc = "slightly more often than not"
    else:
        wr_desc = "less than half the time"

    # Consistency score language
    score_str = ""
    if consistency_score is not None and not pd.isna(consistency_score):
        if consistency_score >= 70:
            score_str = f" The Consistency Score of {consistency_score:.0f}/100 indicates a strong, reliable pattern."
        elif consistency_score >= 45:
            score_str = f" The Consistency Score of {consistency_score:.0f}/100 indicates a moderate pattern -- real but not highly reliable."
        else:
            score_str = f" The Consistency Score of {consistency_score:.0f}/100 is low -- this pattern exists on average but is noisy."

    # Best/worst
    extremes_str = ""
    if best_return is not None and not pd.isna(best_return) and best_year is not None:
        extremes_str += f" The best {month_name} on record was {best_return*100:+.1f}% in {int(best_year)}."
    if worst_return is not None and not pd.isna(worst_return) and worst_year is not None:
        extremes_str += f" The worst was {worst_return*100:+.1f}% in {int(worst_year)}."

    text = (
        f"Over {n_str} years of data, {name} has averaged {ret_str} in {month_name}, "
        f"finishing {direction} {wr_desc} ({wr_str} of years). "
        f"This pattern is {sig_str}.{score_str}{extremes_str}"
    )
    return text


def interpret_rotation(rank1_counts, metric_choice):
    """
    Generate a plain English summary of the asset class rotation result.
    rank1_counts: pd.Series with asset class names as index and count of #1 months as values.
    """
    if rank1_counts.empty:
        return "No rotation data available."

    top_ac    = rank1_counts.index[0]
    top_count = int(rank1_counts.iloc[0])
    bottom_ac = rank1_counts.index[-1]
    bot_count = int(rank1_counts.iloc[-1])

    text = (
        f"Based on {metric_choice.lower()}, {top_ac} ranks first in {top_count} out of 12 months "
        f"historically -- more than any other asset class. "
        f"{bottom_ac} ranks first least often, leading in only {bot_count} month(s). "
        f"This rotation pattern is based on the average across all price series within each class "
        f"and reflects broad historical tendencies, not guarantees."
    )
    return text


def interpret_current_year(series_name, cy_ytd, hist_ytd, months_completed):
    """
    Generate a plain English summary comparing current year to historical average.
    """
    if pd.isna(cy_ytd) or pd.isna(hist_ytd) or months_completed == 0:
        return "Insufficient current year data."

    diff = cy_ytd - hist_ytd
    direction = "ahead of" if diff >= 0 else "behind"
    tracking  = "outperforming" if diff >= 0 else "underperforming"

    text = (
        f"{series_name} has returned {cy_ytd:+.2f}% so far this year "
        f"across {months_completed} completed month(s), "
        f"versus a historical average of {hist_ytd:+.2f}% over the same period. "
        f"It is currently {tracking} its seasonal pattern by {abs(diff):.2f} percentage points -- "
        f"{abs(diff):.2f}pp {direction} historical norms."
    )
    return text


def interpret_decade(series_name, consistent_months, total_decades):
    """
    Generate a plain English summary of decade breakdown stability.
    """
    if not consistent_months:
        return (
            f"No calendar month shows a fully consistent direction for {series_name} "
            f"across all {total_decades} decades analysed. "
            f"The 25-year average may be masking structural shifts over time -- "
            f"interpret seasonal patterns for this series with extra caution."
        )
    months_str = ", ".join(consistent_months)
    return (
        f"For {series_name}, the following months have shown a consistent directional pattern "
        f"(same sign) across all {total_decades} decades: {months_str}. "
        f"These are the most robust seasonal signals -- they have held across very different "
        f"economic environments including the dot-com bust, the global financial crisis, "
        f"and the COVID and inflation cycles."
    )
