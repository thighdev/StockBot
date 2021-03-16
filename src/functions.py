import os
from typing import Union
from dotenv import load_dotenv
from yahoo_fin.stock_info import *
import discord

load_dotenv()
token = os.getenv("RAPID-API-KEY")


def get_movers() -> tuple:
    """
    :return: Embedded details on the top 6 gainers, losers and volume in the US for the day.
    """
    day_gainers = {}
    day_losers = {}
    top_volume = {}
    for k, v in get_day_gainers().to_dict().items():
        if k in ["Name", "Symbol", "Price (Intraday)", "Change", "% Change"]:
            day_gainers[k] = v
        if len(day_gainers) == 5:
            break

    for k, v in get_day_losers().to_dict().items():
        if k in ["Name", "Symbol", "Price (Intraday)", "Change", "% Change"]:
            day_losers[k] = v
        if len(day_losers) == 5:
            break

    for k, v in get_day_most_active().to_dict().items():
        if k in ["Name", "Symbol", "Price (Intraday)", "Change", "% Change", "Volume"]:
            top_volume[k] = v
        if len(top_volume) == 6:
            break

    gainers = discord.Embed(title="Day Gainers:", colour=discord.Colour.green())
    for i in range(0, 6):
        gainers.add_field(
            name=f"**{day_gainers['Name'][i]}**",
            value=f"> Ticker: {day_gainers['Symbol'][i]}\n"
            f"> Price: ${day_gainers['Price (Intraday)'][i]}\n"
            f"> Change: +{day_gainers['Change'][i]}\n"
            f"> % Change: +{round(day_gainers['% Change'][i], 2)}%\n",
        )

    losers = discord.Embed(title="Day Losers:", colour=discord.Colour.red())
    for i in range(0, 6):
        losers.add_field(
            name=f"**{day_losers['Name'][i]}**",
            value=f"> Ticker: {day_losers['Symbol'][i]}\n"
            f"> Price: ${day_losers['Price (Intraday)'][i]}\n"
            f"> Change: {day_losers['Change'][i]}\n"
            f"> % Change: {round(day_losers['% Change'][i], 2)}%\n",
        )

    volume = discord.Embed(title="Top Volume:")
    for i in range(0, 6):
        volume.add_field(
            name=f"**{top_volume['Name'][i]}**",
            value=f"> Ticker: {top_volume['Symbol'][i]}\n"
            f"> Price: ${top_volume['Price (Intraday)'][i]}\n"
            f"> Change: {top_volume['Change'][i]}\n"
            f"> % Change: {round(top_volume['% Change'][i], 2)}%\n"
            f"> Volume: {humanize_number(top_volume['Volume'][i], 1)}\n",
        )

    return gainers, losers, volume


def humanize_number(value: Union[int, float], fraction_point: int = 1) -> str:
    powers = [10 ** x for x in (12, 9, 6, 3, 0)]
    human_powers = ("T", "B", "M", "K", "")
    is_negative = False
    if not isinstance(value, float):
        value = float(value)
    if value < 0:
        is_negative = True
        value = abs(value)
    for i, p in enumerate(powers):
        if value >= p:
            return_value = (
                str(
                    round(value / (p / (10.0 ** fraction_point)))
                    / (10 ** fraction_point)
                )
                + human_powers[i]
            )
            break
    if is_negative:
        return_value = "-" + return_value

    return return_value


def camel_to_title(text: str) -> str:
    formatted = re.sub("([a-z])([A-Z])", "\g<1> \g<2>", text).title()
    return formatted
