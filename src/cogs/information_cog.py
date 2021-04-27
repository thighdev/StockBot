from src.util.Embedder import Embedder
from src.util.SentryHelper import uncaught
from src.util.GraphHandler import plot
from src.positions import *
from src.functions import *
from financelite import *
import pytz
import dateparser


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        help="Requires no arguments, just checks for the top gainers, losses and volume in the US. e.g. !movers",
        brief="Returns the top gainers, losses and volume from the US.",
    )
    async def movers(self, ctx):
        day_gainers, day_losers, top_volume = get_movers()
        await ctx.send(embed=day_gainers)
        await ctx.send(embed=day_losers)
        await ctx.send(embed=top_volume)

    @commands.command()
    async def info(self, ctx, *args):
        group = Group()
        for arg in args:
            group.add_ticker(arg)
        cherrypicks = [
            "shortName",
            "exchange",
            "currency",
            "regularMarketPrice",
            "regularMarketOpen",
            "regularMarketDayRange",
            "regularMarketVolume",
            "averageDailyVolume10Day",
            "averageDailyVolume3Month",
            "regularMarketPreviousClose",
            "fiftyDayAverage",
            "fiftyTwoWeekRange",
        ]
        try:
            group_info = group.get_quotes(cherrypicks=cherrypicks)
        except DataRequestException:
            msg = "Invalid ticker(s). Please check if you have correct tickers."
            return await ctx.send(embed=Embedder.error(msg))
        for i, stock_info in enumerate(group_info):
            embed = discord.Embed(
                title=f"Information for {args[i].upper()}", colour=discord.Colour.blue()
            )
            for cherry in cherrypicks:
                key = camel_to_title(cherry)
                value = stock_info.get(cherry)
                if isinstance(value, float):
                    value = format(value, ".2f")
                if isinstance(value, int):
                    value = humanize_number(value)
                embed.add_field(name=key, value=value)
            await ctx.send(embed=embed)

    @commands.command(
        help="Requires one argument, ticker. Example !news TSLA",
        brief="Returns recent news related to the specified ticker",
    )
    async def news(self, ctx, ticker: str, region: str = "US", lang: str = "en-US"):
        try:
            items = News(region=region, lang=lang).get_news(ticker, count=9)
        except NoNewsFoundException:
            return await ctx.send(
                embed=Embedder.error("No news was found with this ticker")
            )
        embed = discord.Embed(
            title=f"News for {ticker.upper()}", colour=discord.Colour.gold()
        )
        est = pytz.timezone("US/Eastern")
        for i in items:
            title = i.get("title")
            date = i.get("published")
            parsed_date = dateparser.parse(date).astimezone(est)
            parsed_date = parsed_date.strftime("%b %d, %Y %-I:%M%p EST")
            link = i.get("link")
            embed.add_field(name=title, value=f"[{parsed_date}]({link})", inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    async def live(self, ctx, ticker: str):
        stock = Stock(ticker)
        try:
            live_price, currency = stock.get_live()
        except DataRequestException as e:
            return await ctx.send(
                embed=Embedder.error(f"{str(e).upper()} is not a valid ticker")
            )

        embed = Embedder.embed(
            title=ticker.upper(), message=f"${format(live_price, '.2f')} {currency}"
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def hist(self, ctx, ticker: str, data_range: str):
        stock = Stock(ticker)
        try:
            hist_dictionary = stock.get_hist(data_range=data_range)
            hist_data, currency, start, end = hist_dictionary.values()
            start, end = epoch_to_datetime_tz([start, end], tz="EST")
            time_delta_days = (end - start).days
            start = start.strftime("%a, %b %d, %Y")
            end = end.strftime("%a, %b %d, %Y")
            diff = hist_data[-1] - hist_data[0]
            is_positive = ""
            if diff < 0:
                colour = discord.Colour.red()
            else:
                is_positive = "+"
                colour = discord.Colour.green()
            diff_percent = diff / hist_data[0] * 100
            embed = discord.Embed(
                title=f"{ticker.upper()} from {start} to {end}",
                description=f"{is_positive}{format(diff, '.2f')} {currency} "
                f"({is_positive}{format(diff_percent, '.2f')}%)\nFrom **{time_delta_days} days ago** to today.",
                colour=colour,
            )
            await ctx.send(embed=embed)
        except DataRequestException:
            return await ctx.send(
                embed=Embedder.error(
                    "`!hist ticker data_range`\n"
                    "Data ranges:\n"
                    "13d = 13 **trading** days\n"
                    "2wk = 2 **calendar** weeks\n"
                    "5mo = 5 **calendar** months\n"
                    "3y = 3 **calendar** years"
                )
            )

    @hist.error
    async def hist_error(self, ctx, error: Exception):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                embed=Embedder.error(
                    "`!hist ticker data_range`\n"
                    "Data ranges:\n"
                    "13d = 13 **trading** days\n"
                    "2wk = 2 **calendar** weeks\n"
                    "5mo = 5 **calendar** months\n"
                    "3y = 3 **calendar** years"
                )
            )
        await ctx.send(embed=Embedder.error(uncaught(error)))

    @commands.command()
    async def graph(self, ctx, ticker: str, data_range: str = "1d"):
        stock = Stock(ticker)
        if data_range in ["1d", "5d"]:
            interval = "5m"
        elif data_range in ["1mo", "3mo", "6mo"]:
            interval = "1h"
        elif data_range in ["1y", "2y", "ytd"]:
            interval = "1d"
        else:
            interval = "1wk"
        try:
            chart = stock.get_chart(interval=interval, range=data_range)
        except DataRequestException:
            return await ctx.send(embed=Embedder.error("Invalid ticker"))
        in_mem = io.BytesIO(plot(chart))
        chart = discord.File(in_mem, filename=f"{ticker.upper()}-{data_range}.png")
        in_mem.close()
        await ctx.send(file=chart)
