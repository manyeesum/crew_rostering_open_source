"""Market Barometer -- a market-timing situation-awareness panel.

A composite, multi-signal "warning-light" monitor built from the Five Star
Charts technical-analysis methodology (market breadth, over-extension,
distribution, volatility/news regime and a macro/stagflation overlay).

The core idea, in the channel's own words: these are not tools to *guess the
top*; they are an observation framework -- the more lights that come on, the
more you trim exposure.
"""

from .barometer import BarometerResult, compute_barometer          # noqa: F401
from .datasources import MarketData, synthetic_market, yfinance_market  # noqa: F401
from .report import render                                          # noqa: F401
