"""
The barometer scoring engine.

This turns raw indicators + breadth into the Five Star Charts "warning-light
panel". The presenter's own framing drives the whole design:

    "These indicators are not for guessing the top. They are an observation
     framework -- the more lights that come on, the more you shrink exposure;
     if nothing is lit, you don't shrink."   (Signal-summary, video #2)

So we compute six lights (his five signals + a macro overlay), each a 0..1
"warning intensity", combine them into a 0..100 *Caution Score*, and map that to
an exposure stance. We never emit a naked "SELL EVERYTHING" -- we emit "how many
lights are on and how much to trim", which is the whole point of the method.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from . import breadth as br
from . import indicators as ind
from .config import BANDS, LIGHT_WEIGHTS, TH


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------
@dataclass
class Check:
    name: str
    intensity: float          # 0 = all-clear, 1 = full warning; NaN = no data
    detail: str = ""


@dataclass
class Light:
    key: str
    title: str
    signal: str               # the presenter's label, e.g. "Signal #1 指鑽"
    weight: float
    checks: list = field(default_factory=list)

    @property
    def intensity(self) -> float:
        vals = [c.intensity for c in self.checks if not _isnan(c.intensity)]
        return float(np.mean(vals)) if vals else float("nan")

    @property
    def status(self) -> str:
        i = self.intensity
        if _isnan(i):
            return "N/A"
        if i < 0.33:
            return "GREEN"
        if i < 0.66:
            return "AMBER"
        return "RED"


@dataclass
class BarometerResult:
    asof: str
    caution_score: float
    band: str
    guidance: str
    regime: str
    lights_lit: int
    lights_total: int
    lights: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    context: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _isnan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def ramp(v: float, zero_at: float, one_at: float) -> float:
    """Linear warning ramp: 0 at ``zero_at`` -> 1 at ``one_at`` (clamped).

    Works in either direction (``one_at`` may be below ``zero_at``).
    """
    if _isnan(v) or zero_at == one_at:
        return float("nan")
    t = (v - zero_at) / (one_at - zero_at)
    return float(min(1.0, max(0.0, t)))


def _last(s: Optional[pd.Series]) -> float:
    if s is None or len(s) == 0:
        return float("nan")
    s = s.dropna()
    return float(s.iloc[-1]) if len(s) else float("nan")


def _is_near_high(series: pd.Series, window: int = 20, tol: float = 0.01) -> bool:
    """Is the last value within ``tol`` of its ``window``-day high?"""
    s = series.dropna()
    if len(s) < window:
        return False
    return s.iloc[-1] >= s.iloc[-window:].max() * (1 - tol)


# ---------------------------------------------------------------------------
# Individual lights
# ---------------------------------------------------------------------------
def _light_breadth(market) -> Light:
    L = Light("breadth_divergence", "Breadth / Participation",
              "Signal #1  指鑽 (breadth divergence)", LIGHT_WEIGHTS["breadth_divergence"])
    closes = market.constituents_close
    idx_close = market.index["close"]
    index_high = _is_near_high(idx_close, 20)

    if closes is not None and closes.shape[1] >= 5:
        p50 = br.pct_above_ma(closes, 50)
        t2108 = br.pct_above_ma(closes, 40)
        ad = br.advance_decline(closes)
        thrust = br.thrust_days(closes)

        v50 = _last(p50)
        L.checks.append(Check(
            "% above 50-day MA", ramp(v50, TH["pct_above_50_hi"], TH["pct_above_50_lo"]),
            f"{v50:.0f}% (weak <{TH['pct_above_50_lo']:.0f}, healthy >{TH['pct_above_50_hi']:.0f})"))

        vt = _last(t2108)
        L.checks.append(Check(
            "T2108 (% above 40-day)", ramp(vt, TH["t2108_hi"], TH["t2108_lo"]),
            f"{vt:.0f}%  (video cited 63%->39% into the top)"))

        # A-D line divergence vs the index (index new high, A-D line not)
        ad_line = ad["ad_line"]
        ad_high = _is_near_high(ad_line, 20)
        div = 1.0 if (index_high and not ad_high) else 0.0
        L.checks.append(Check(
            "A-D line divergence", div,
            "index at 20-day high but A-D line is NOT" if div else "A-D confirming"))

        # thrust: trailing net (up4% - down4%) over 10 sessions
        net_thrust = float(thrust["net"].iloc[-10:].sum())
        L.checks.append(Check(
            "4%+ thrust balance (10d)", ramp(net_thrust, TH["thrust_net_lo"], TH["thrust_net_hi"]),
            f"net {net_thrust:+.0f} (down-4% days dominating is bearish)"))

        # up/down volume distribution
        if market.constituents_volume is not None:
            udv = br.up_down_volume(closes, market.constituents_volume)
            vu = float(udv.iloc[-10:].mean())
            L.checks.append(Check(
                "up/down volume (10d avg)", ramp(vu, TH["updown_vol_hi"], TH["updown_vol_lo"]),
                f"{vu:.2f} (<1 = distribution under the surface)"))

        # McClellan Oscillator negative while the index presses its highs
        mo = _last(br.mcclellan_oscillator(closes))
        mo_intensity = ramp(mo, TH["mcclellan_lo"], TH["mcclellan_hi"]) if index_high else 0.0
        L.checks.append(Check(
            "McClellan oscillator", mo_intensity,
            f"{mo:+.0f} {'while index at highs' if index_high else '(index not at highs)'}"))

        # Net new 52-week highs-lows deteriorating while index high
        if len(closes) >= 150:
            nh = _last(br.net_new_highs(closes))
            nh_intensity = ramp(nh, TH["nhnl_lo"], TH["nhnl_hi"]) if index_high else 0.0
            L.checks.append(Check(
                "net new 52wk highs-lows", nh_intensity,
                f"{nh:+.0f} (negative at index highs = Hindenburg-style split tape)"))

    # sector breadth + defensive rotation
    if market.sector_close is not None and market.sector_close.shape[1] >= 3:
        sec20 = _last(br.sectors_above_ma(market.sector_close, 20))
        L.checks.append(Check(
            "% sectors above 20-day", ramp(sec20, TH["sectors_above20_hi"], TH["sectors_above20_lo"]),
            f"{sec20:.0f}% (only defensives left = topping)"))
        rot = br.defensive_vs_cyclical(market.sector_close)
        vr = _last(rot)
        L.checks.append(Check(
            "defensive rotation (21d)", ramp(vr, TH["defensive_rot_lo"], TH["defensive_rot_hi"]),
            f"{vr:+.1f}% def/cyc (rising = money playing defense)"))
        ra = _last(br.risk_appetite_ratio(market.sector_close))
        L.checks.append(Check(
            "risk appetite XLY/XLP (21d)", ramp(ra, TH["risk_appetite_lo"], TH["risk_appetite_hi"]),
            f"{ra:+.1f}% (falling = risk appetite leaving)"))
    return L


def _light_momentum(market) -> Light:
    L = Light("momentum_extension", "Momentum / Over-extension",
              "Signal #2  能減 (deceleration & stretch)", LIGHT_WEIGHTS["momentum_extension"])
    idx = market.index
    close, high, low = idx["close"], idx["high"], idx["low"]

    d50 = _last(ind.distance_from_ma_atr(high, low, close, 50))
    L.checks.append(Check(
        "distance from 50-day (ATRs)", ramp(d50, TH["dist50_atr_lo"], TH["dist50_atr_hi"]),
        f"{d50:.1f}x ATR (>5x stretched; video cited ~7x)"))

    if len(close) >= 200:
        d200 = _last(ind.distance_from_ma_pct(close, 200))
        L.checks.append(Check(
            "distance from 200-day (%)", ramp(d200, TH["dist200_pct_lo"], TH["dist200_pct_hi"]),
            f"{d200:+.0f}% (2000 peak ~90%, AI leaders ~50-60%)"))

    bb = ind.bollinger(close, 20, 2.0)
    pctb = _last(bb["pct_b"])
    L.checks.append(Check(
        "Bollinger %B", ramp(pctb, TH["pctb_lo"], TH["pctb_hi"]),
        f"{pctb:.2f} (>1 = riding above the upper band)"))

    # RSI bearish divergence
    r = ind.rsi(close, 14)
    dv = ind.bearish_divergence(close, r, lookback=60)
    L.checks.append(Check(
        "RSI bearish divergence", 1.0 if dv.get("detected") else 0.0,
        "price higher-high, RSI lower-high" if dv.get("detected") else "no divergence"))

    # MACD histogram fading while price near highs
    m = ind.macd(close)
    hist = m["hist"].dropna()
    fading = bool(_is_near_high(close, 20) and len(hist) > 10 and hist.iloc[-1] < hist.iloc[-10])
    L.checks.append(Check(
        "MACD momentum fade", 1.0 if fading else 0.0,
        "new price high on weaker MACD" if fading else "momentum confirming"))
    return L


def _light_failed_breakouts(market) -> Light:
    L = Light("failed_breakouts", "Failed Breakouts",
              "Signal #3  突破失敗", LIGHT_WEIGHTS["failed_breakouts"])
    closes = market.constituents_close
    if closes is not None and closes.shape[1] >= 5:
        rate = br.failed_breakout_rate(closes)
        L.checks.append(Check(
            "failed 20-day breakouts", ramp(rate, TH["failbo_lo"], TH["failbo_hi"]),
            f"{rate*100:.0f}% of recent breakouts rolled back" if not _isnan(rate) else "no recent breakouts"))
    win = market.manual.get("win_rate")
    if win is not None:
        L.checks.append(Check(
            "personal win-rate", ramp(float(win), TH["winrate_hi"], TH["winrate_lo"]),
            f"{float(win)*100:.0f}% (video: 70%->below 40% = danger)"))
    return L


def _light_distribution(market) -> Light:
    L = Light("distribution", "Distribution / High-Vol Down Days",
              "Signal #4  高波下跌日", LIGHT_WEIGHTS["distribution"])
    idx = market.index
    if "volume" in idx:
        dd = ind.distribution_days(idx["close"], idx["volume"])
        L.checks.append(Check(
            "distribution days (25d)", ramp(dd, TH["dist_days_lo"], TH["dist_days_hi"]),
            f"{dd} days (4-5+ is the classic warning cluster)"))
        hv = ind.high_volatility_down_days(idx["high"], idx["low"], idx["close"], idx["volume"])
        L.checks.append(Check(
            "high-vol down days (25d)", ramp(hv, TH["hivol_down_lo"], TH["hivol_down_hi"]),
            f"{hv} wide-range heavy-volume down days"))
    return L


def _light_news_regime(market) -> Light:
    L = Light("news_regime", "Volatility & News Regime",
              "Signal #5  市場對消息有反應", LIGHT_WEIGHTS["news_regime"])
    # Volatility spike while the market falls (proxy for regime flip)
    if market.vix is not None and len(market.vix) > 6:
        vix = market.vix.dropna()
        vix_chg = (vix.iloc[-1] / vix.iloc[-6] - 1.0) * 100.0
        idx_ret = market.index["close"].pct_change(5).iloc[-1] * 100.0
        spike = vix_chg if idx_ret < 0 else 0.0
        L.checks.append(Check(
            "VIX spike on weakness", ramp(spike, TH["vix_spike_lo"], TH["vix_spike_hi"]),
            f"VIX {vix_chg:+.0f}% / 5d while index {idx_ret:+.1f}%"))
        # Absolute volatility level (video: VXN/VIX >30 = 'not a safe market')
        lvl = float(vix.iloc[-1])
        L.checks.append(Check(
            "volatility level", ramp(lvl, 18.0, 32.0),
            f"{lvl:.0f} (>25 caution, >30 danger)"))
        # Vol rising WHILE the index rises = big traders buying protection into
        # strength = hedged distribution (the VXN-up-with-NDX point, video #4).
        if len(vix) > 21:
            vix20 = (vix.iloc[-1] / vix.iloc[-21] - 1.0) * 100.0
            idx20 = market.index["close"].pct_change(20).iloc[-1] * 100.0
            hedging = (vix20 > 10 and idx20 > 0)
            L.checks.append(Check(
                "vol rising into strength (hedging)", 1.0 if hedging else 0.0,
                f"VIX {vix20:+.0f}% & index {idx20:+.0f}% /20d" if hedging else "no hedging divergence"))
    # VIX term structure: VIX/VIX3M approaching or above 1.0 = backwardation
    # (front-end fear). >0.95 warning, >1.0 confirmed stress (see RESEARCH.md).
    if market.vix is not None and market.vix3m is not None:
        v, v3 = market.vix.dropna(), market.vix3m.dropna()
        if len(v) and len(v3):
            ts = float(v.iloc[-1]) / float(v3.iloc[-1])
            L.checks.append(Check(
                "VIX term structure (VIX/VIX3M)", ramp(ts, TH["vix_ts_lo"], TH["vix_ts_hi"]),
                f"{ts:.2f} (>0.95 warning, >1.0 backwardation)"))
    if market.manual.get("put_call_complacent") is not None:
        pc = market.manual["put_call_complacent"]
        L.checks.append(Check(
            "put/call complacency", 1.0 if pc else 0.0,
            "equity put/call at complacent extreme" if pc else "options positioning normal"))
    nr = market.manual.get("news_reaction_negative")
    if nr is not None:
        L.checks.append(Check(
            "market selling bad news", 1.0 if nr else 0.0,
            "market now SELLS bad news / prices rate hikes" if nr else "shrugging off bad news (strong)"))
    return L


def _light_macro(market) -> Light:
    """Stagflation / macro overlay (video #3). Fed by manual macro inputs since
    this box cannot pull live macro series."""
    L = Light("macro_overlay", "Macro / Stagflation Overlay",
              "Inflation - Rates - Growth", LIGHT_WEIGHTS["macro_overlay"])
    m = market.manual
    nfib = m.get("nfib")
    if nfib is not None:
        L.checks.append(Check(
            "NFIB small-biz optimism", ramp(float(nfib), 100.0, 90.0),
            f"{float(nfib):.1f} (52y avg ~98; 95.3 cited = weakening)"))
    ppi = m.get("ppi_yoy")
    if ppi is not None:
        L.checks.append(Check(
            "PPI YoY (producer inflation)", ramp(float(ppi), 2.0, 6.0),
            f"{float(ppi):.1f}% (leads CPI; video cited 6.5%)"))
    if m.get("stagflation") is not None:
        L.checks.append(Check(
            "stagflation regime", 1.0 if m["stagflation"] else 0.0,
            "high inflation + slowing growth" if m["stagflation"] else "no stagflation"))
    if m.get("yield_10y_rising") is not None:
        L.checks.append(Check(
            "10Y yield rising / Treasury dumping", 1.0 if m["yield_10y_rising"] else 0.0,
            "US/JP 10Y climbing, USD pressure" if m["yield_10y_rising"] else "yields contained"))
    if m.get("yield_curve_steepening") is not None:
        L.checks.append(Check(
            "bear steepener (long up, short down)", 1.0 if m["yield_curve_steepening"] else 0.0,
            "30Y up / 2Y down = bad for tech" if m["yield_curve_steepening"] else "curve stable"))
    if m.get("yield_curve_uninverting") is not None:
        L.checks.append(Check(
            "yield curve un-inverting", 1.0 if m["yield_curve_uninverting"] else 0.0,
            "2s10s re-steepening after inversion — recessions typically start here"
            if m["yield_curve_uninverting"] else "no un-inversion signal"))
    if m.get("sahm_rule_triggered") is not None:
        L.checks.append(Check(
            "Sahm rule", 1.0 if m["sahm_rule_triggered"] else 0.0,
            "unemployment 3m-avg +0.5pt off its 12m low = recession onset"
            if m["sahm_rule_triggered"] else "Sahm rule not triggered"))
    if m.get("credit_spreads_widening") is not None:
        L.checks.append(Check(
            "credit spreads widening", 1.0 if m["credit_spreads_widening"] else 0.0,
            "HY spreads widening (credit smells trouble first)"
            if m["credit_spreads_widening"] else "credit calm"))
    # --- sentiment / positioning extremes (contrarian top signals) ---
    if m.get("margin_debt_extreme") is not None:
        L.checks.append(Check(
            "margin debt at extreme", 1.0 if m["margin_debt_extreme"] else 0.0,
            "record leverage (2000/2007 analog)" if m["margin_debt_extreme"] else "leverage contained"))
    if m.get("euphoria") is not None:
        L.checks.append(Check(
            "sentiment euphoria / FOMO", 1.0 if m["euphoria"] else 0.0,
            "leveraged-ETF chasing, retail all-in" if m["euphoria"] else "sentiment normal"))
    if m.get("homebuilders_diverging") is not None:
        L.checks.append(Check(
            "homebuilders/construction divergence", 1.0 if m["homebuilders_diverging"] else 0.0,
            "XHB not confirming = recession tell" if m["homebuilders_diverging"] else "housing confirming"))

    # --- seasonality (auto from the date): sell-in-May + midterm-election year ---
    ts = market.index.index[-1]
    if hasattr(ts, "month"):
        month, year = ts.month, ts.year
        season = 0.0
        if 5 <= month <= 9:                 # weak "sell in May .. Sept" window
            season += 0.4
        if year % 4 == 2:                   # US midterm-election year (historically weak)
            season += 0.4
        L.checks.append(Check(
            "seasonality window", min(1.0, season),
            f"{ts.date()} (May-Sep weak; midterm year = {'yes' if year % 4 == 2 else 'no'})"))
    return L


# ---------------------------------------------------------------------------
# Regime label ("zero-line" bull/bear structure from video #3)
# ---------------------------------------------------------------------------
def _regime_label(market) -> str:
    close = market.index["close"].dropna()
    if len(close) < 200:
        return "INSUFFICIENT-HISTORY"
    ma200 = ind.sma(close, 200)
    ma50 = ind.sma(close, 50)
    last = close.iloc[-1]
    above200 = last > ma200.iloc[-1]
    slope200 = ma200.iloc[-1] > ma200.iloc[-21]
    golden = ma50.iloc[-1] > ma200.iloc[-1]
    # fraction of last 40 sessions spent above the 200-day (the "zero line")
    frac_above = float((close.iloc[-40:] > ma200.iloc[-40:]).mean())
    if above200 and slope200 and golden:
        return "BULL (price above rising 200-day, golden cross)"
    if not above200 and not slope200:
        return "BEAR (price below falling 200-day)"
    if above200 and frac_above < 0.6:
        return "TRANSITION (whipsawing the 200-day 'zero line')"
    return "NEUTRAL / late-cycle chop"


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------
def compute_barometer(market) -> BarometerResult:
    lights = [
        _light_breadth(market),
        _light_momentum(market),
        _light_failed_breakouts(market),
        _light_distribution(market),
        _light_news_regime(market),
        _light_macro(market),
    ]

    # Weighted caution score over the lights that actually have data.
    num = 0.0
    den = 0.0
    lit = 0
    for L in lights:
        if _isnan(L.intensity):
            continue
        num += L.weight * L.intensity
        den += L.weight
        if L.status in ("AMBER", "RED"):
            lit += 1
    caution = (num / den * 100.0) if den > 0 else float("nan")

    band, guidance = "N/A", "insufficient data"
    if not _isnan(caution):
        for lo, hi, name, text in BANDS:
            if (lo <= caution < hi) or (hi == 100 and caution == 100):
                band, guidance = name, text
                break

    # Collect the headline flags (red or notable checks).
    flags = []
    for L in lights:
        for c in L.checks:
            if not _isnan(c.intensity) and c.intensity >= 0.66:
                flags.append(f"[{L.title}] {c.name}: {c.detail}")

    asof = str(market.index.index[-1].date()) if hasattr(market.index.index[-1], "date") \
        else str(market.index.index[-1])

    return BarometerResult(
        asof=asof,
        caution_score=round(caution, 1) if not _isnan(caution) else float("nan"),
        band=band,
        guidance=guidance,
        regime=_regime_label(market),
        lights_lit=lit,
        lights_total=sum(1 for L in lights if not _isnan(L.intensity)),
        lights=lights,
        flags=flags,
        context={
            "index_last": round(float(market.index["close"].iloc[-1]), 2),
        },
    )
