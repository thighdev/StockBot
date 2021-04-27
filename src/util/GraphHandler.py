import io

import pandas as pd
import mplfinance as mpf
from src.functions import epoch_to_datetime_tz

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


def process_chart_data(chart: dict) -> tuple:
    result = chart.get("result").pop()
    meta = result.get("meta")
    tz = meta.get("exchangeTimezoneName")
    timezone_short = meta.get("timezone")
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
    return symbol, currency, timezone_short, df


def plot(chart: dict) -> bytes:
    data = process_chart_data(chart)
    symbol, currency, tz, df = data
    index = df.index
    plot_type = "candle"
    fig, axes = mpf.plot(
        df,
        type=plot_type,
        mav=(50, 100, 200),
        volume=True,
        style=STYLE,
        title=f"\n{symbol} Stock Price from {index[0].strftime('%Y-%m-%d')} to {index[-1].strftime('%Y-%m-%d')} {tz}",
        ylabel=f"$ Price in {currency}",
        ylabel_lower="Volume",
        returnfig=True,
    )
    axes[0].legend(
        ["50 MA", "100 MA", "200 MA"],
        loc="lower left",
        bbox_to_anchor=(1, 1),
    )
    close = df["Close"]
    max_idx, min_idx = close.idxmax(), close.idxmin()
    max_val, min_val = df.at[max_idx, "Close"], df.at[min_idx, "Close"]
    max_idx = df.index.get_loc(max_idx)
    min_idx = df.index.get_loc(min_idx)
    recent_idx = df.index[-1]
    recent_val = df.at[recent_idx, "Close"]
    recent_idx = df.index.get_loc(recent_idx)
    axes[0].annotate(
        f"Local Min @ {format(min_val, '.2f')}",
        xy=(min_idx, min_val),
        xytext=(50, -50),
        textcoords="offset pixels",
        arrowprops=dict(arrowstyle="->"),
    )
    axes[0].annotate(
        f"Local Max @ {format(max_val, '.2f')}",
        xy=(max_idx, max_val),
        xytext=(0, 50),
        textcoords="offset pixels",
        arrowprops=dict(arrowstyle="->"),
    )
    axes[0].annotate(
        f"Recent Close @ {format(recent_val, '.2f')}",
        xy=(recent_idx, recent_val),
        xytext=(50, 50),
        textcoords="offset pixels",
        arrowprops=dict(arrowstyle="->"),
    )

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=200)
    buffer.seek(0)
    img_in_bytes = buffer.read()
    buffer.close()
    return img_in_bytes
