import pandas as pd
import mplfinance as mpf
from datetime import datetime
from pytz import timezone
from typing import List

STYLE = {
    "base_mpl_style": "fast",
    "marketcolors": {
        "candle": {"up": "#00b060", "down": "#fe3032"},
        "edge": {"up": "#00b060", "down": "#fe3032"},
        "wick": {"up": "#606060", "down": "#606060"},
        "ohlc": {"up": "#00b060", "down": "#fe3032"},
        "volume": {"up": "#4dc790", "down": "#fd6b6c"},
        "vcedge": {"up": "#1f77b4", "down": "#1f77b4"},
        "vcdopcod": True,
        "alpha": 0.9,
    },
    "mavcolors": None,
    "facecolor": "#fafafa",
    "gridcolor": "#d0d0d0",
    "gridstyle": "-",
    "y_on_right": False,
    "rc": {
        "axes.labelcolor": "#101010",
        "axes.edgecolor": "f0f0f0",
        "axes.grid.axis": "y",
        "ytick.color": "#101010",
        "xtick.color": "#101010",
        "figure.titlesize": "x-large",
        "figure.titleweight": "semibold",
    },
    "base_mpf_style": "yahoo",
}


def epoch_to_datetime_tz(epoch_list: List[int], tz: str = "UTC"):
    tz = timezone(tz)
    return [datetime.fromtimestamp(i, tz) for i in epoch_list]


def process_chart_data(chart: dict) -> tuple:
    result = chart.get("result").pop()
    meta = result.get("meta")
    tz = meta.get("exchangeTimezoneName")
    symbol = meta.get("symbol")
    currency = meta.get("currency")
    timestamps = result.get("timestamp")
    datetime_idx = epoch_to_datetime_tz(timestamps, tz=tz)
    quote = result.get("indicators").get("quote").pop()
    lows = quote.get("low")
    highs = quote.get("high")
    opens = quote.get("open")
    closes = quote.get("close")
    volumes = quote.get("volume")
    data = zip(opens, closes, highs, lows, volumes)
    df = pd.DataFrame(
        data, index=datetime_idx, columns=["Open", "Close", "High", "Low", "Volume"]
    )
    return symbol, currency, df


def plot(chart: dict):
    data = process_chart_data(chart)
    symbol, currency, df = data
    index = df.index
    fig, axes = mpf.plot(
        df,
        type="candle",
        mav=(12, 26),
        volume=True,
        style=STYLE,
        title=f"\n{symbol} Stock Price from {index[0].strftime('%Y-%m-%d')} to {index[-1].strftime('%Y-%m-%d')}",
        ylabel=f"$ Price in {currency}",
        ylabel_lower="Volume",
        returnfig=True,
    )
    axes[0].legend(["12 Moving Average", "26 Moving Average"])
    fig.savefig("src/mpl_output/test.png")
