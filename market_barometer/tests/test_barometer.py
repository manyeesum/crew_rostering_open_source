"""
Behavioral contract for the Market Barometer.

These tests are the project's regression gate (see GOVERNANCE.md §6). The
non-negotiable invariant is DISCRIMINATION: the engine must score a healthy
tape clearly lower than a topping tape. If a change breaks that, the change is
wrong — not the test.

Run either way:
    python -m pytest market_barometer/tests -q
    python -m market_barometer.tests.test_barometer
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from market_barometer import barometer as bar
from market_barometer import breadth as br
from market_barometer import indicators as ind
from market_barometer.barometer import compute_barometer, ramp
from market_barometer.datasources import MarketData, synthetic_market


# ---------------------------------------------------------------------------
# indicators
# ---------------------------------------------------------------------------
def test_rsi_bounds_and_extremes():
    up = pd.Series(np.linspace(100, 200, 60))
    down = pd.Series(np.linspace(200, 100, 60))
    r_up, r_down = ind.rsi(up).dropna(), ind.rsi(down).dropna()
    assert (r_up <= 100).all() and (r_up >= 0).all()
    assert r_up.iloc[-1] > 90            # straight-up tape -> RSI ~100
    assert r_down.iloc[-1] < 10          # straight-down tape -> RSI ~0


def test_sma_and_distance_from_ma():
    s = pd.Series(np.arange(1.0, 61.0))
    assert abs(ind.sma(s, 5).iloc[-1] - 58.0) < 1e-9
    d = ind.distance_from_ma_pct(s, 20)
    assert d.iloc[-1] > 0                # rising series sits above its MA


def test_atr_positive_and_bollinger_pctb():
    n = 80
    close = pd.Series(100 + np.sin(np.arange(n) / 5.0))
    high, low = close * 1.01, close * 0.99
    assert (ind.atr(high, low, close).dropna() > 0).all()
    bb = ind.bollinger(close)
    pb = bb["pct_b"].dropna()
    assert (pb > -0.5).all() and (pb < 1.5).all()


def test_distribution_days_counts_down_days_on_higher_volume():
    close = pd.Series([100, 99, 98, 99, 97.5, 97.0] * 5)
    vol = pd.Series([1e6 * (1 + 0.1 * i) for i in range(30)])  # always rising
    assert ind.distribution_days(close, vol, window=25) >= 5


# ---------------------------------------------------------------------------
# breadth
# ---------------------------------------------------------------------------
def test_pct_above_ma_known_frame():
    n = 60
    up = 100 + np.arange(n) * 1.0        # ends above its MA
    dn = 100 - np.arange(n) * 1.0        # ends below its MA
    closes = pd.DataFrame({"UP1": up, "UP2": up * 1.1, "DN1": dn, "DN2": dn * 0.9})
    val = br.pct_above_ma(closes, 20).iloc[-1]
    assert abs(val - 50.0) < 1e-9        # 2 of 4 above


def test_pct_above_ma_no_valid_rows_is_nan_not_crash():
    closes = pd.DataFrame({"A": np.arange(10.0), "B": np.arange(10.0)})
    out = br.pct_above_ma(closes, 50)    # window longer than history
    assert out.isna().all()


def test_failed_breakout_rate_no_breakouts_is_nan():
    n = 60
    flat = pd.DataFrame({f"S{i}": 100 - np.arange(n) * 0.1 for i in range(6)})
    rate = br.failed_breakout_rate(flat)
    assert rate != rate                  # NaN


def test_mcclellan_sign_tracks_breadth():
    n = 120
    up = pd.DataFrame({f"U{i}": 100 + np.arange(n) * 1.0 for i in range(6)})
    dn = pd.DataFrame({f"D{i}": 100 - np.arange(n) * 0.5 for i in range(6)})
    assert br.mcclellan_oscillator(up).dropna().iloc[-1] > 0
    assert br.mcclellan_oscillator(dn).dropna().iloc[-1] < 0


def test_risk_appetite_ratio_direction_and_missing_columns():
    n = 60
    sec = pd.DataFrame({"XLY": 100 - np.arange(n) * 0.5,      # discretionary falling
                        "XLP": 100 + np.arange(n) * 0.5})     # staples rising
    ra = br.risk_appetite_ratio(sec)
    assert ra.dropna().iloc[-1] < 0                            # risk-off
    assert br.risk_appetite_ratio(sec[["XLY"]]).empty          # graceful when missing


def test_vix_term_structure_check_present():
    res = compute_barometer(synthetic_market("topping"))
    news = [L for L in res.lights if L.key == "news_regime"][0]
    names = [c.name for c in news.checks]
    assert "VIX term structure (VIX/VIX3M)" in names


def test_advance_decline_shapes():
    closes = pd.DataFrame({"A": [1, 2, 3, 2], "B": [1, 1, 2, 3], "C": [3, 2, 1, 1]},
                          dtype=float)
    ad = br.advance_decline(closes)
    assert list(ad.columns) == ["advancers", "decliners", "net", "ad_line"]
    assert ad["ad_line"].iloc[-1] == ad["net"].sum()


# ---------------------------------------------------------------------------
# scoring engine
# ---------------------------------------------------------------------------
def test_ramp_both_directions_and_clamping():
    assert ramp(5.0, 0.0, 10.0) == 0.5
    assert ramp(-1.0, 0.0, 10.0) == 0.0
    assert ramp(11.0, 0.0, 10.0) == 1.0
    assert ramp(50.0, 60.0, 40.0) == 0.5      # inverted (lower = worse)
    assert ramp(float("nan"), 0.0, 10.0) != ramp(float("nan"), 0.0, 10.0)  # NaN


def test_discrimination_healthy_vs_topping():
    """THE core invariant: healthy tape scores clearly below topping tape."""
    healthy = compute_barometer(synthetic_market("healthy"))
    topping = compute_barometer(synthetic_market("topping"))
    assert healthy.caution_score < 20, healthy.caution_score
    assert topping.caution_score > 40, topping.caution_score
    assert healthy.lights_lit == 0
    assert topping.lights_lit >= 4
    assert healthy.band == "RISK-ON"
    assert topping.band in ("CAUTION", "DEFENSIVE", "RISK-OFF")


def test_minimal_market_index_only_does_not_crash():
    """Engine must degrade gracefully with only benchmark OHLCV (no breadth)."""
    n = 120
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2025-01-01", periods=n)
    close = pd.Series(500 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, n))), index=dates)
    idx = pd.DataFrame({
        "open": close.shift(1).fillna(close.iloc[0]),
        "high": close * 1.005, "low": close * 0.995,
        "close": close, "volume": pd.Series(1e9, index=dates),
    })
    res = compute_barometer(MarketData(index=idx))
    assert res.regime == "INSUFFICIENT-HISTORY"      # < 200 sessions
    assert res.caution_score == res.caution_score    # still a number

    from market_barometer.report import render
    out = render(res)
    assert "CAUTION SCORE" in out


def test_seasonality_midterm_flag():
    m = synthetic_market("healthy")
    L = bar._light_macro(m)
    season = [c for c in L.checks if c.name == "seasonality window"]
    assert season, "seasonality check must always be present"


# ---------------------------------------------------------------------------
# plain-python runner (no pytest needed)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    failures = 0
    for name, fn in sorted({k: v for k, v in globals().items()
                            if k.startswith("test_") and callable(v)}.items()):
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {name}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
