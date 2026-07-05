"""
Cross-sectional market-breadth metrics.

These operate on a *universe* of constituents at once (a DataFrame whose columns
are tickers and whose index is dates). Breadth is the heart of the Five Star
Charts method: "when the index makes new highs but fewer stocks participate, the
top is forming" (Signal #1, 指鑽 / breadth divergence).

Everything returns a time series so the scoring layer can look at both the
*level* today and the *trend* (is participation rolling over while the index
still climbs?).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind


def pct_above_ma(closes: pd.DataFrame, n: int) -> pd.Series:
    """Percent of constituents trading above their own ``n``-day SMA, over time.

    ``pct_above_ma(closes, 40)`` is the classic **T2108** the presenter quotes
    ("63% at the high, 39% now"). n=20/50/200 give the other participation lines.
    """
    ma = closes.rolling(n, min_periods=n).mean()
    above = (closes > ma) & ma.notna()
    valid = ma.notna()
    denom = valid.sum(axis=1).replace(0, np.nan)
    return 100.0 * above.sum(axis=1) / denom


def advance_decline(closes: pd.DataFrame) -> pd.DataFrame:
    """Daily advancers/decliners and the cumulative Advance-Decline line.

    The A-D line making *lower highs* while the index makes *higher highs* is the
    textbook breadth divergence (2021Q4 -> 2022 top in the video).
    """
    chg = closes.diff()
    advancers = (chg > 0).sum(axis=1)
    decliners = (chg < 0).sum(axis=1)
    net = advancers - decliners
    ad_line = net.cumsum()
    return pd.DataFrame(
        {"advancers": advancers, "decliners": decliners, "net": net, "ad_line": ad_line}
    )


def thrust_days(closes: pd.DataFrame, threshold: float = 0.04) -> pd.DataFrame:
    """Count of stocks moving +/- ``threshold`` each day (the '4%+ movers').

    Healthy markets print bursts of "up 4%" breadth; as a top forms the "down
    4%" side dominates ("deep red days"). Signal #1.
    """
    ret = closes.pct_change()
    up = (ret >= threshold).sum(axis=1)
    down = (ret <= -threshold).sum(axis=1)
    return pd.DataFrame({"up": up, "down": down, "net": up - down})


def net_new_highs(closes: pd.DataFrame, window: int = 252) -> pd.Series:
    """Net new 52-week highs minus lows across the universe, per day."""
    roll_max = closes.rolling(window, min_periods=window // 2).max()
    roll_min = closes.rolling(window, min_periods=window // 2).min()
    new_high = (closes >= roll_max).sum(axis=1)
    new_low = (closes <= roll_min).sum(axis=1)
    return new_high - new_low


def up_down_volume(closes: pd.DataFrame, volumes: pd.DataFrame) -> pd.Series:
    """Up-volume / down-volume ratio across the universe, per day.

    Persistent readings below 1 while price rises = distribution under the hood.
    """
    chg = closes.diff()
    up_mask = chg > 0
    down_mask = chg < 0
    up_vol = volumes.where(up_mask).sum(axis=1)
    down_vol = volumes.where(down_mask).sum(axis=1)
    return up_vol / down_vol.replace(0.0, np.nan)


def sectors_above_ma(sector_closes: pd.DataFrame, n: int = 20) -> pd.Series:
    """Percent of sector ETFs above their ``n``-day MA.

    "As of Friday, more than half the sectors are below their 20-day line, and
    the only ones above are defensives" -- Signal #1 sector-breadth read.
    """
    return pct_above_ma(sector_closes, n)


def defensive_vs_cyclical(
    sector_closes: pd.DataFrame,
    defensives=("XLU", "XLP", "XLV"),
    cyclicals=("XLK", "XLY", "XLF", "XLI"),
    window: int = 21,
) -> pd.Series:
    """Relative strength of a defensive basket vs a cyclical basket.

    A *rising* line = money rotating into utilities/staples/health = late-cycle
    "the smart money is playing defense" warning (Signal #1/#4 rotation).
    Returns the ``window``-day change of the defensive/cyclical ratio, in %.
    """
    have = [c for c in list(defensives) + list(cyclicals) if c in sector_closes.columns]
    d = [c for c in defensives if c in sector_closes.columns]
    c = [c for c in cyclicals if c in sector_closes.columns]
    if not d or not c:
        return pd.Series(dtype=float)
    # Equal-weight normalised baskets.
    norm = sector_closes[have] / sector_closes[have].iloc[0]
    defensive = norm[d].mean(axis=1)
    cyclical = norm[c].mean(axis=1)
    ratio = defensive / cyclical
    return (ratio / ratio.shift(window) - 1.0) * 100.0


def failed_breakout_rate(
    closes: pd.DataFrame, breakout_window: int = 20, check_window: int = 5
) -> float:
    """Fraction of recent 20-day-high breakouts that failed back into range.

    Market-wide proxy for Signal #3 (突破失敗 / failed breakouts). For each
    stock that closed at a new ``breakout_window``-day high within the last
    ``check_window`` days, we check whether it has since closed back below that
    breakout level. High readings = breakouts aren't sticking = weak tape.
    """
    failures = 0
    breakouts = 0
    prior_high = closes.rolling(breakout_window, min_periods=breakout_window).max().shift(1)
    broke = closes >= prior_high
    for col in closes.columns:
        recent = broke[col].iloc[-(check_window + 1) : -1]
        if not recent.any():
            continue
        # index of the most recent breakout day within the check window
        bo_dates = recent[recent].index
        bo_date = bo_dates[-1]
        bo_level = float(prior_high[col].loc[bo_date])
        breakouts += 1
        if float(closes[col].iloc[-1]) < bo_level:
            failures += 1
    if breakouts == 0:
        return float("nan")
    return failures / breakouts
