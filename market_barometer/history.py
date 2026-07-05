"""
Caution-score history tracking (the ``--save-history`` flag).

Each run appends one row per date to a CSV: the Caution Score, stance band,
lights lit, regime, and every light's intensity. Re-running on the same date
replaces that date's row (no duplicates). The file opens directly in Excel /
Google Sheets, so the score-over-time chart comes for free.
"""

from __future__ import annotations

import math
import os

import pandas as pd

_BLOCKS = "▁▂▃▄▅▆▇█"


def save_history(result, path: str) -> pd.DataFrame:
    """Append ``result`` to the history CSV at ``path`` and return the table."""
    score = result.caution_score
    row = {
        "date": result.asof,
        "caution_score": None if (isinstance(score, float) and math.isnan(score)) else score,
        "band": result.band,
        "lights_lit": result.lights_lit,
        "lights_total": result.lights_total,
        "regime": result.regime,
    }
    for L in result.lights:
        i = L.intensity
        row[f"light_{L.key}"] = None if (isinstance(i, float) and math.isnan(i)) else round(i, 3)

    new = pd.DataFrame([row])
    if os.path.exists(path):
        old = pd.read_csv(path)
        old = old[old["date"].astype(str) != str(row["date"])]
        new = pd.concat([old, new], ignore_index=True)
    new = new.sort_values("date").reset_index(drop=True)
    new.to_csv(path, index=False)
    return new


def render_trend(df: pd.DataFrame, n: int = 10) -> str:
    """A small terminal trend view of the last ``n`` readings."""
    tail = df.dropna(subset=["caution_score"]).tail(n)
    if tail.empty:
        return ""
    scores = tail["caution_score"].astype(float).tolist()
    spark = "".join(_BLOCKS[min(7, max(0, int(s / 100 * 7.999)))] for s in scores)
    lines = ["", f"  HISTORY (last {len(tail)} readings)   {spark}"]
    for _, r in tail.iterrows():
        lines.append(f"    {r['date']}   {float(r['caution_score']):5.1f}/100   "
                     f"{r['band']:<12} lights {r['lights_lit']}/{r['lights_total']}")
    return "\n".join(lines)
