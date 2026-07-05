"""
StockCharts CSV ingestion.

StockCharts members can download historical data for any symbol (including the
official market-breadth symbols) as CSV/TXT. This adapter reads a folder of
those files and returns the "official" breadth series the scoring engine
prefers over our computed universe approximations.

IMPORTANT: this is a *file reader*, deliberately not a scraper. StockCharts'
terms prohibit automated/robotic access; the intended workflow is a human
member downloading files from their own account, then pointing the CLI at the
folder with ``--stockcharts-dir``.

Recognized symbols (filename stem, with or without the $/! prefix, any case):

    $SPXA50R   -> pct_above_50     % of S&P 500 stocks above their 50-day MA
    $SPXA200R  -> pct_above_200    % above their 200-day MA
    $SPXA150R  -> pct_above_150    % above their 150-day MA
    $NYAD      -> ad_net           NYSE daily net advances (A-D); cumsum = A-D line
    $NYHL      -> net_new_highs    NYSE net new 52-week highs-lows
    $NYA50R    -> nyse_above_50    % of NYSE stocks above their 50-day MA
    !GT40SPX   -> t2108            % above 40-day MA (T2108-style participation)

Files may be named e.g. ``$NYAD.csv``, ``NYAD.csv`` or ``nyad.txt``. Expected
content: a Date column plus OHLC/Close columns (StockCharts' standard export);
the 'Close' column is taken as the indicator value.
"""

from __future__ import annotations

import os
import re
from typing import Dict

import pandas as pd

SYMBOL_MAP = {
    "SPXA50R": "pct_above_50",
    "SPXA200R": "pct_above_200",
    "SPXA150R": "pct_above_150",
    "NYAD": "ad_net",
    "NYHL": "net_new_highs",
    "NYA50R": "nyse_above_50",
    "GT40SPX": "t2108",
}


def _normalise_stem(filename: str) -> str:
    stem = os.path.splitext(os.path.basename(filename))[0]
    return re.sub(r"[^A-Z0-9]", "", stem.upper())


def _read_series(path: str) -> pd.Series:
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    date_col = next((c for c in df.columns if "date" in c), df.columns[0])
    value_col = "close" if "close" in df.columns else None
    if value_col is None:
        numeric = [c for c in df.columns if c != date_col
                   and pd.api.types.is_numeric_dtype(df[c])]
        if not numeric:
            raise ValueError(f"{path}: no numeric value column found")
        value_col = numeric[-1]
    s = pd.Series(
        pd.to_numeric(df[value_col], errors="coerce").values,
        index=pd.to_datetime(df[date_col], errors="coerce"),
    )
    s = s[s.index.notna()].dropna().sort_index()
    if s.empty:
        raise ValueError(f"{path}: parsed no usable rows")
    return s


def load_stockcharts_dir(path: str) -> Dict[str, pd.Series]:
    """Read every recognized symbol file in ``path``.

    Returns a dict keyed by the canonical names in ``SYMBOL_MAP`` values.
    Unrecognized files are skipped silently; unreadable recognized files raise,
    since silently dropping data the user downloaded would be worse.
    """
    out: Dict[str, pd.Series] = {}
    if not os.path.isdir(path):
        raise FileNotFoundError(f"StockCharts data folder not found: {path}")
    for fname in sorted(os.listdir(path)):
        if not fname.lower().endswith((".csv", ".txt")):
            continue
        key = SYMBOL_MAP.get(_normalise_stem(fname))
        if key is None:
            continue
        out[key] = _read_series(os.path.join(path, fname))
    return out
