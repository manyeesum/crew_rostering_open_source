"""
Single-series technical indicators.

Pure functions that operate on price/volume ``pandas`` Series or DataFrames.
Nothing here talks to the network or knows about the barometer scoring model --
these are the raw building blocks the higher layers consume.

Where an indicator maps onto the Five Star Charts methodology it is noted in the
docstring (e.g. "distance from 50-day in ATR units" -> Signal #2 "能減 /
overextension").
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Moving averages
# ---------------------------------------------------------------------------
def sma(series: pd.Series, n: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(n, min_periods=n).mean()


def ema(series: pd.Series, n: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=n, adjust=False, min_periods=n).mean()


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------
def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's Relative Strength Index."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100 - 100 / (1 + rs)
    # When there are no losses RSI is defined as 100.
    return out.where(avg_loss != 0, 100.0)


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """MACD line, signal line and histogram."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


# ---------------------------------------------------------------------------
# Volatility / bands
# ---------------------------------------------------------------------------
def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """Average True Range (Wilder smoothing)."""
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands plus %B and bandwidth.

    ``pct_b`` > 1 means price is *above* the upper band -- Signal #2, the
    channel's "riding above the weekly Bollinger band" over-extension warning.
    """
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    upper = mid + k * sd
    lower = mid - k * sd
    pct_b = (close - lower) / (upper - lower)
    bandwidth = (upper - lower) / mid
    return pd.DataFrame(
        {"mid": mid, "upper": upper, "lower": lower, "pct_b": pct_b, "bandwidth": bandwidth}
    )


# ---------------------------------------------------------------------------
# Extension from a moving average  (Signal #2: 能減 / over-extension)
# ---------------------------------------------------------------------------
def distance_from_ma_pct(close: pd.Series, n: int) -> pd.Series:
    """Percent distance of price above/below its ``n``-day SMA.

    The dot-com-vs-AI comparison in the video is exactly this metric measured
    on the leaders' 200-day MA (2000 peak ~90%, AI names now ~50-60%).
    """
    ma = sma(close, n)
    return (close / ma - 1.0) * 100.0


def distance_from_ma_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, n: int = 50, atr_n: int = 14
) -> pd.Series:
    """Distance of price above its ``n``-day SMA expressed in ATR units.

    This is the presenter's preferred over-extension gauge: ">5x ATR above the
    50-day is already very extended; the index is now ~7x."
    """
    ma = sma(close, n)
    a = atr(high, low, close, atr_n)
    return (close - ma) / a


# ---------------------------------------------------------------------------
# Bearish divergence  (Signal #1 & #2: price higher-high, oscillator lower-high)
# ---------------------------------------------------------------------------
def _swing_highs(series: pd.Series, order: int = 5) -> pd.Series:
    """Boolean mask of local maxima (a bar higher than ``order`` neighbours each side)."""
    vals = series.values
    n = len(vals)
    mask = np.zeros(n, dtype=bool)
    for i in range(order, n - order):
        window = vals[i - order : i + order + 1]
        if np.isnan(window).any():
            continue
        if vals[i] == window.max() and (window == vals[i]).sum() == 1:
            mask[i] = True
    return pd.Series(mask, index=series.index)


def bearish_divergence(
    price: pd.Series, oscillator: pd.Series, lookback: int = 60, order: int = 5
) -> dict:
    """Detect a bearish divergence between ``price`` and an ``oscillator``.

    Returns a dict with ``detected`` plus the two swing points compared. A
    divergence is flagged when the two most recent price swing-highs are rising
    while the oscillator's readings at those points are falling.
    """
    p = price.iloc[-lookback:]
    o = oscillator.reindex(p.index)
    highs = _swing_highs(p, order=order)
    idx = list(p.index[highs.values])
    if len(idx) < 2:
        return {"detected": False, "reason": "insufficient swing highs"}
    t1, t2 = idx[-2], idx[-1]
    price_hh = p.loc[t2] > p.loc[t1]
    osc_lh = o.loc[t2] < o.loc[t1]
    return {
        "detected": bool(price_hh and osc_lh),
        "price_prev": float(p.loc[t1]),
        "price_last": float(p.loc[t2]),
        "osc_prev": float(o.loc[t1]),
        "osc_last": float(o.loc[t2]),
        "t_prev": str(t1.date()) if hasattr(t1, "date") else str(t1),
        "t_last": str(t2.date()) if hasattr(t2, "date") else str(t2),
    }


# ---------------------------------------------------------------------------
# Distribution days  (Signal #4: 高波下跌日 / institutional selling)
# ---------------------------------------------------------------------------
def distribution_days(
    close: pd.Series,
    volume: pd.Series,
    window: int = 25,
    down_threshold: float = 0.002,
) -> int:
    """Count IBD-style distribution days in the last ``window`` sessions.

    A distribution day = index closes down more than ``down_threshold`` on
    volume higher than the prior session (institutions selling into strength).
    Four-to-five in a rolling 25-day window is the classic warning cluster.
    """
    ret = close.pct_change()
    higher_vol = volume > volume.shift(1)
    is_dist = (ret <= -down_threshold) & higher_vol
    return int(is_dist.iloc[-window:].sum())


def high_volatility_down_days(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    window: int = 25,
    atr_n: int = 14,
    range_mult: float = 1.5,
) -> int:
    """Count 'high-volatility down days' (高波下跌日) in the last ``window``.

    A wide-range down close (true range > ``range_mult`` x ATR) on above-average
    volume -- the abrupt distribution days the presenter circles on the chart.
    """
    tr = true_range(high, low, close)
    a = atr(high, low, close, atr_n)
    avg_vol = volume.rolling(50, min_periods=10).mean()
    down = close < close.shift(1)
    wide = tr > range_mult * a
    heavy = volume > avg_vol
    flag = down & wide & heavy
    return int(flag.iloc[-window:].sum())
