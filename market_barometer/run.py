"""
CLI entry point.

    # No network needed -- prove the engine on a synthetic "topping" tape:
    python -m market_barometer.run --source synthetic --scenario topping
    python -m market_barometer.run --source synthetic --scenario healthy

    # Live, on your own machine (needs Yahoo Finance access):
    python -m market_barometer.run --source yfinance --period 2y

Macro/sentiment overlays that can't be pulled automatically (NFIB, PPI, margin
debt, euphoria, yield curve, homebuilder divergence, news regime) can be passed
with --macro key=value,... e.g.

    --macro nfib=95.3,ppi_yoy=6.5,stagflation=1,margin_debt_extreme=1,euphoria=1
"""

from __future__ import annotations

import argparse

from . import datasources as ds
from .barometer import compute_barometer
from .report import render


def _parse_macro(s: str | None) -> dict:
    out: dict = {}
    if not s:
        return out
    for kv in s.split(","):
        if "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        k, v = k.strip(), v.strip()
        low = v.lower()
        if low in ("1", "true", "yes", "y"):
            out[k] = True
        elif low in ("0", "false", "no", "n"):
            out[k] = False
        else:
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Market Barometer — situation-awareness panel")
    p.add_argument("--source", choices=["synthetic", "yfinance"], default="synthetic")
    p.add_argument("--scenario", choices=["healthy", "topping"], default="topping",
                   help="only used with --source synthetic")
    p.add_argument("--period", default="2y", help="yfinance history window")
    p.add_argument("--macro", default=None, help="key=value,... macro/sentiment overlays")
    p.add_argument("--stockcharts-dir", default=None,
                   help="folder of StockCharts CSV downloads ($NYAD, $SPXA50R, ...); "
                        "official series override computed approximations")
    p.add_argument("--save-history", nargs="?", const="barometer_history.csv",
                   default=None, metavar="CSV",
                   help="append today's reading to a history CSV (default: "
                        "barometer_history.csv) and show the recent trend")
    args = p.parse_args(argv)

    macro = _parse_macro(args.macro)

    if args.source == "yfinance":
        market = ds.yfinance_market(period=args.period, manual=macro)
    else:
        market = ds.synthetic_market(scenario=args.scenario)
        if macro:
            market.manual.update(macro)

    if args.stockcharts_dir:
        from .stockcharts import load_stockcharts_dir
        market.official = load_stockcharts_dir(args.stockcharts_dir)
        print(f"[stockcharts] loaded official series: {sorted(market.official)}")

    result = compute_barometer(market)
    print(render(result))

    if args.save_history:
        from .history import render_trend, save_history
        df = save_history(result, args.save_history)
        print(f"\n  saved to {args.save_history} ({len(df)} readings)")
        trend = render_trend(df)
        if trend:
            print(trend)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
