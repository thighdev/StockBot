from discord.ext import tasks
from financelite import Stock
from datetime import datetime
from pytz import timezone
import discord

cst = timezone("US/Central")


@tasks.loop(seconds=15.0)
async def start_live(message, tickers: list):
    now = datetime.now(tz=cst).strftime("%c")
    prices = discord.Embed(
        title=f"Live ticker data @ {now}", colour=discord.Colour.green()
    )
    for ticker in tickers:
        stock = Stock(ticker).get_live()
        prices.add_field(name=ticker.upper(), value=f"${stock[0]} {stock[1]}")

    await message.edit(embed=prices)
