"""
Data sources for the barometer.

``MarketData`` is the bundle every scoring function consumes. Two ways to build
it:

* ``synthetic_market(...)`` -- self-contained, deterministic, no network. Used
  for tests/demos and to prove the engine end-to-end (this sandbox blocks live
  market data). It can generate a healthy tape or an engineered "topping" tape.

* ``yfinance_market(...)`` -- pulls real OHLCV via ``yfinance`` for the index,
  the breadth universe, the sector ETFs and the VIX. Run this on your own
  machine where Yahoo Finance is reachable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from . import config


@dataclass
class MarketData:
    index: pd.DataFrame                              # OHLCV for the benchmark
    constituents_close: Optional[pd.DataFrame] = None
    constituents_volume: Optional[pd.DataFrame] = None
    sector_close: Optional[pd.DataFrame] = None
    vix: Optional[pd.Series] = None
    vix3m: Optional[pd.Series] = None                # 3-month implied vol (^VIX3M)
    manual: dict = field(default_factory=dict)       # macro/sentiment overlays


# ---------------------------------------------------------------------------
# Synthetic market (no network)
# ---------------------------------------------------------------------------
def synthetic_market(scenario: str = "topping", n_days: int = 420, seed: int = 7) -> MarketData:
    """Build a deterministic synthetic market.

    ``scenario='healthy'`` -> broad participation, benign internals.
    ``scenario='topping'`` -> the index grinds to new highs on a handful of
    "generals" while the rest of the tape rolls over, volatility creeps up and
    distribution days appear -- i.e. every light *should* start blinking.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n_days)
    tickers = config.BREADTH_UNIVERSE
    n_names = len(tickers)
    generals = set(tickers[:8])           # mega-cap leaders

    # --- constituent price paths ---
    closes = {}
    volumes = {}
    for i, t in enumerate(tickers):
        drift = 0.0006
        vol = 0.014
        rets = rng.normal(drift, vol, n_days)
        if scenario == "topping":
            # Last ~50 days: generals melt up, everyone else quietly rolls over.
            tail = slice(n_days - 50, n_days)
            if t in generals:
                rets[tail] = rng.normal(0.007, 0.012, 50)      # parabolic leaders
            else:
                rets[tail] = rng.normal(-0.003, 0.018, 50)     # breadth decay
        price = 100 * np.exp(np.cumsum(rets))
        closes[t] = price
        base_vol = rng.uniform(5e6, 5e7)
        volumes[t] = base_vol * (1 + 0.3 * rng.standard_normal(n_days))

    closes = pd.DataFrame(closes, index=dates)
    volumes = pd.DataFrame(volumes, index=dates).abs()

    # --- benchmark index: cap-weighted, generals dominate (like SPY/QQQ) ---
    weights = np.array([3.0 if t in generals else 1.0 for t in tickers])
    weights = weights / weights.sum()
    idx_close = (closes * weights).sum(axis=1)
    idx_close = idx_close / idx_close.iloc[0] * 500.0            # scale near SPY

    # Inject genuine distribution days (real down closes) into the last 25.
    dist_offsets = (5, 12, 19) if scenario == "topping" else ()
    for off in dist_offsets:
        idx_close.iloc[n_days - off] = idx_close.iloc[n_days - off - 1] * 0.982

    # Fabricate OHLC + volume around the (final) index close.
    intraday = 0.003
    idx_ret = idx_close.pct_change().fillna(0.0)
    idx_open = idx_close.shift(1).fillna(idx_close.iloc[0])
    idx_high = np.maximum(idx_close, idx_open) * (1 + intraday)
    idx_low = np.minimum(idx_close, idx_open) * (1 - intraday)
    idx_vol = pd.Series(6e10 * (1 + 0.2 * rng.standard_normal(n_days)), index=dates).abs()
    idx_vol = idx_vol * np.where(idx_ret.values < 0, 1.5, 0.9)   # heavier on down days
    for off in dist_offsets:
        d = dates[n_days - off]
        idx_low.loc[d] = idx_close.loc[d] * (1 - 0.015)          # wide range
        idx_vol.loc[d] *= 2.2                                    # heavy volume

    index = pd.DataFrame(
        {"open": idx_open, "high": idx_high, "low": idx_low, "close": idx_close, "volume": idx_vol}
    )

    # --- sector ETFs ---
    sectors = {}
    for j, s in enumerate(config.SECTOR_ETFS):
        drift = 0.0005
        rets = rng.normal(drift, 0.012, n_days)
        if scenario == "topping":
            tail = slice(n_days - 40, n_days)
            if s in config.DEFENSIVE_SECTORS:
                rets[tail] = rng.normal(0.0015, 0.010, 40)     # defensives lead
            elif s in ("XLK", "XLC"):
                rets[tail] = rng.normal(0.003, 0.014, 40)      # tech melt-up
            else:
                rets[tail] = rng.normal(-0.002, 0.013, 40)     # cyclicals fade
        sectors[s] = 50 * np.exp(np.cumsum(rets))
    sector_close = pd.DataFrame(sectors, index=dates)

    # --- VIX ---
    if scenario == "topping":
        base = np.linspace(14, 15, n_days)
        base[n_days - 30:] = np.linspace(15, 29, 30)           # vol creeps up into the top
    else:
        base = 14 + rng.normal(0, 1.0, n_days)
    vix = pd.Series(np.clip(base + rng.normal(0, 0.6, n_days), 9, 60), index=dates)
    # Term structure: healthy contango (VIX3M well above VIX); topping tape's
    # front end catches up toward backwardation (ratio -> ~0.97).
    ts_ratio = 0.97 if scenario == "topping" else 0.84
    vix3m = vix / ts_ratio

    # --- macro / sentiment overlay (what you'd read off FRED / news) ---
    if scenario == "topping":
        manual = dict(
            nfib=95.3, ppi_yoy=6.5, stagflation=True, yield_10y_rising=True,
            yield_curve_steepening=True, margin_debt_extreme=True, euphoria=True,
            homebuilders_diverging=True, news_reaction_negative=False, win_rate=0.42,
            sahm_rule_triggered=False, yield_curve_uninverting=True,
            credit_spreads_widening=True, put_call_complacent=True,
        )
    else:
        manual = dict(
            nfib=101.0, ppi_yoy=2.2, stagflation=False, yield_10y_rising=False,
            margin_debt_extreme=False, euphoria=False, homebuilders_diverging=False,
            win_rate=0.62, sahm_rule_triggered=False, yield_curve_uninverting=False,
            credit_spreads_widening=False, put_call_complacent=False,
        )

    return MarketData(
        index=index, constituents_close=closes, constituents_volume=volumes,
        sector_close=sector_close, vix=vix, vix3m=vix3m, manual=manual,
    )


# ---------------------------------------------------------------------------
# Live market via yfinance (run on your own machine)
# ---------------------------------------------------------------------------
def yfinance_market(period: str = "2y", manual: Optional[dict] = None) -> MarketData:
    """Download a live ``MarketData`` bundle with yfinance.

    Requires network access to Yahoo Finance (blocked in the build sandbox, fine
    on your laptop). ``manual`` carries the macro/sentiment overlays you read off
    FRED / your broker (NFIB, PPI, margin debt, euphoria, yield curve, ...).
    """
    import yfinance as yf

    def _download(tickers):
        raw = yf.download(tickers, period=period, auto_adjust=True,
                          progress=False, group_by="ticker")
        return raw

    tickers = [config.BENCHMARK] + config.BREADTH_UNIVERSE + config.SECTOR_ETFS
    data = _download(tickers)

    def _field(tkr, field):
        try:
            return data[tkr][field]
        except Exception:
            return None

    bench = config.BENCHMARK
    index = pd.DataFrame({
        "open": _field(bench, "Open"), "high": _field(bench, "High"),
        "low": _field(bench, "Low"), "close": _field(bench, "Close"),
        "volume": _field(bench, "Volume"),
    }).dropna()

    cons_close = pd.DataFrame({t: _field(t, "Close") for t in config.BREADTH_UNIVERSE}).dropna(how="all")
    cons_vol = pd.DataFrame({t: _field(t, "Volume") for t in config.BREADTH_UNIVERSE}).dropna(how="all")
    sect_close = pd.DataFrame({t: _field(t, "Close") for t in config.SECTOR_ETFS}).dropna(how="all")

    def _download_series(ticker):
        try:
            raw = yf.download(ticker, period=period, auto_adjust=True, progress=False)
            s = raw["Close"] if "Close" in raw else raw.iloc[:, 0]
            return s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s
        except Exception:
            return None

    vix = _download_series(config.VIX)
    vix3m = _download_series(config.VIX3M)

    return MarketData(
        index=index, constituents_close=cons_close, constituents_volume=cons_vol,
        sector_close=sect_close, vix=vix, vix3m=vix3m, manual=manual or {},
    )
