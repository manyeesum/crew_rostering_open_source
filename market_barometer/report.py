"""Human-readable rendering of a ``BarometerResult`` for the terminal."""

from __future__ import annotations

from .barometer import BarometerResult

_DOT = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴", "N/A": "⚪"}


def _bar(score: float, width: int = 40) -> str:
    if score != score:  # NaN — no scorable lights had data
        return "[" + "?" * width + "] n/a"
    filled = int(round(score / 100 * width))
    return "[" + "#" * filled + "-" * (width - filled) + f"] {score:.0f}/100"


def render(res: BarometerResult) -> str:
    lines = []
    lines.append("=" * 66)
    lines.append("  MARKET BAROMETER  —  situation-awareness panel")
    lines.append("  (framework after Five Star Charts: count the lights, don't guess the top)")
    lines.append("=" * 66)
    lines.append(f"  As of:   {res.asof}     Index: {res.context.get('index_last')}")
    lines.append(f"  Regime:  {res.regime}")
    lines.append("")
    lines.append(f"  CAUTION SCORE  {_bar(res.caution_score)}")
    lines.append(f"  STANCE:  {res.band}  —  {res.guidance}")
    lines.append(f"  Lights lit: {res.lights_lit}/{res.lights_total}"
                 "   (more lit = trim more exposure)")
    lines.append("-" * 66)

    for L in res.lights:
        pct = "" if L.status == "N/A" else f"{L.intensity*100:>3.0f}%"
        lines.append(f"  {_DOT[L.status]} {L.title:<34} {L.status:<6} {pct}")
        lines.append(f"       {L.signal}")
        for c in L.checks:
            mark = "·"
            if not (c.intensity != c.intensity):  # not NaN
                mark = "!" if c.intensity >= 0.66 else ("~" if c.intensity >= 0.33 else " ")
            lines.append(f"        {mark} {c.name:<32} {c.detail}")
        lines.append("")

    if res.flags:
        lines.append("-" * 66)
        lines.append("  ⚠  LIT WARNINGS:")
        for f in res.flags:
            lines.append(f"     • {f}")
    lines.append("=" * 66)
    lines.append("  Educational tool only. Not investment advice.")
    lines.append("=" * 66)
    return "\n".join(lines)
