import discord
from src.functions import *
from discord.ext import commands
from pretty_help import PrettyHelp
from src.util.Embedder import *
from src.util.SentryHelper import uncaught
from src.positions import buy_position, sell_position, get_portfolio, NoPositionsException
from src.database import Session, connect
from financelite import *
import pytz
import dateparser
import sentry_sdk

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
SENTRY_DSN = os.getenv("SENTRY_DSN")
dev_prefix = os.getenv("DEV_PREFIX")
prefix = "!" if not dev_prefix else dev_prefix
bot = commands.Bot(command_prefix=prefix, help_command=PrettyHelp(no_category='Commands'))


@bot.command(
    help="Requires no arguments, just checks for the top gainers, losses and volume in the US. e.g. !movers",
    brief="Returns the top gainers, losses and volume from the US.")
async def movers(ctx):
    day_gainers, day_losers, top_volume = get_movers()
    await ctx.send(embed=day_gainers)
    await ctx.send(embed=day_losers)
    await ctx.send(embed=top_volume)


@bot.command()
async def info(ctx, *args):
    group = Group()
    for arg in args:
        group.add_ticker(arg)
    cherrypicks = ['shortName', 'exchange', 'currency',
                   'regularMarketPrice', 'regularMarketOpen', 'regularMarketDayRange',
                   'regularMarketVolume', 'averageDailyVolume10Day', 'averageDailyVolume3Month',
                   'regularMarketPreviousClose', 'fiftyDayAverage', 'fiftyTwoWeekRange'
                   ]
    group_info = group.get_quotes(cherrypicks=cherrypicks)
    for i, stock_info in enumerate(group_info):
        embed = discord.Embed(title=f"Information for {args[i].upper()}",
                              colour=discord.Colour.blue())
        for cherry in cherrypicks:
            key = camel_to_title(cherry)
            value = stock_info.get(cherry)
            if isinstance(value, float):
                value = format(value, '.2f')
            if isinstance(value, int):
                value = humanize_number(value)
            embed.add_field(name=key, value=value)
        await ctx.send(embed=embed)


@info.error
async def info_error(ctx, error: Exception):
    if isinstance(error, commands.CommandError):
        msg = error
    elif isinstance(error, DataRequestException):
        msg = "Invalid ticker(s). Please check if you have correct tickers."
    else:
        msg = uncaught(error)
    await ctx.send(embed=Embedder.error(msg))


@bot.command(
    help="Requires one argument, ticker. Example !news TSLA",
    brief="Returns recent news related to the specified ticker")
async def news(ctx, ticker: str, region: str = "US", lang: str = "en-US"):
    items = News(region=region, lang=lang).get_news(ticker, count=9)
    embed = discord.Embed(title=f"News for {ticker.upper()}", colour=discord.Colour.gold())
    est = pytz.timezone('US/Eastern')
    for i in items:
        title = i.get("title")
        date = i.get("published")
        parsed_date = dateparser.parse(date).astimezone(est)
        parsed_date = parsed_date.strftime("%b %d, %Y %-I:%M%p EST")
        link = i.get("link")
        embed.add_field(name=title, value=f"[{parsed_date}]({link})", inline=True)
    await ctx.send(embed=embed)


@news.error
async def news_error(ctx, error: Exception):
    if isinstance(error, commands.CommandError):
        msg = "Came across an error while processing your request."
    elif isinstance(error, NoNewsFoundException):
        msg = "No news was found with this ticker."
    else:
        msg = uncaught(error)
    await ctx.send(embed=Embedder.error(msg))


@bot.command()
async def live(ctx, ticker: str):
    stock = Stock(ticker)
    live_price, currency = stock.get_live()
    embed = Embedder.embed(title=ticker.upper(), message=f"${format(live_price, '.2f')} {currency}")
    await ctx.send(embed=embed)


@live.error
async def live_error(ctx, error: Exception):
    if isinstance(error, commands.CommandInvokeError):
        msg = """
        Came across an error while processing your request.
        Check if your region corresponds to the proper exchange,
        or re-check the ticker you used.
        """
    else:
        msg = uncaught(error)
    await ctx.send(embed=Embedder.error(msg))


@bot.command()
async def hist(ctx, ticker: str, days: int):
    stock = Stock(ticker)
    data, currency = stock.get_hist(days=days)
    diff = data[-1] - data[0]
    is_positive = ""
    if diff < 0:
        colour = discord.Colour.red()
    else:
        is_positive = "+"
        colour = discord.Colour.green()
    diff_percent = diff / data[0] * 100
    embed = discord.Embed(title=f"Historical change for {ticker.upper()} within {days} days",
                          description=f"{is_positive}{format(diff, '.2f')} {currency} "
                                      f"({is_positive}{format(diff_percent, '.2f')}%)",
                          colour=colour)
    await ctx.send(embed=embed)


@hist.error
async def hist_error(ctx, error: Exception):
    if isinstance(error, ValueError) or isinstance(error, commands.BadArgument):
        msg = "Days should be an integer larger than 1"
    elif isinstance(error, commands.MissingRequiredArgument):
        msg = "`!hist [ticker (KBO)] [days (15)]`"
    else:
        msg = error
    await ctx.send(embed=Embedder.error(msg))



@bot.command()
async def buy(ctx, ticker: str, amount: int, price: float = None):
    session = Session()
    ticker_price, total, currency = calculate_total(ticker=ticker, amount=amount, price=price)
    ticker = ticker.upper()
    is_usd = True if currency == "USD" else False
    user_id = str(ctx.message.author.id)
    username = ctx.message.author.name
    buy_complete = buy_position(session=session, user_id=user_id, username=username,
                                symbol=ticker, amount=amount, price=ticker_price, is_usd=is_usd)
    if buy_complete:
        embed = Embedder.embed(title=f"Successfully bought ${ticker}",
                               message=f"{ticker} x {amount} @{ticker_price} {currency}\n"
                                       f"`Total: ${'{:.2f}'.format(total)}  {currency}`")
    else:
        embed = Embedder.error("Something went wrong.")
    await ctx.send(embed=embed)


@buy.error
async def buy_error(ctx, error: Exception):
    if isinstance(error, commands.BadArgument):
        msg = "Bad argument;\n`!buy [ticker (KBO)] [amount (13)] [price (12.50)(optional)]`"
    elif isinstance(error, commands.CommandInvokeError):
        msg = "Invalid ticker."
    elif isinstance(error, commands.MissingRequiredArgument):
        msg = "Missing arguments;\n`!buy [ticker (KBO)] [amount (13)] [price (12.50)(optional)]`"
    else:
        msg = uncaught(error)
    await ctx.send(embed=Embedder.error(msg))


@bot.command()
async def sell(ctx, ticker: str, amount: int, price: float = None):
    session = Session()
    ticker_price, total, currency = calculate_total(ticker=ticker, amount=amount, price=price)
    ticker = ticker.upper()
    user_id = str(ctx.message.author.id)
    username = ctx.message.author.name
    sell_complete = sell_position(session=session, user_id=user_id, username=username,
                                  symbol=ticker, amount=amount, price=ticker_price)
    if sell_complete:
        embed = Embedder.embed(title=f"Successfully Sold ${ticker}",
                               message=f"{ticker} x {amount} @{ticker_price} {currency}\n"
                                       f"`Total: ${'{:.2f}'.format(total)}  {currency}`")
    else:
        embed = Embedder.error("Check if you have enough positions to sell!")
    await ctx.send(embed=embed)


@sell.error
async def sell_error(ctx, error: Exception):
    if isinstance(error, commands.BadArgument):
        msg = "Bad argument;\n`!sell [ticker (KBO)] [amount (13)] [price (12.50)]`"
    elif isinstance(error, commands.CommandInvokeError):
        msg = "Invalid ticker."
    else:
        msg = uncaught(error)
    await ctx.send(embed=Embedder.error(msg))


@bot.command()  # TODO: add profit/loss for portfolio summary
async def portfolio(ctx, mobile: str = ""):
    if mobile and mobile not in ("m", "mobile"):
        raise discord.ext.commands.BadArgument
    session = Session()
    user_id = ctx.author.id
    username = ctx.author.name
    mobile = bool(mobile)
    portfolio_complete = get_portfolio(session=session, user_id=user_id, username=username, mobile=mobile)
    if portfolio_complete and mobile:
        await ctx.send(embed=portfolio_complete[0])
        await ctx.send(embed=portfolio_complete[1])
    else:
        await ctx.send(f"""```{portfolio_complete[0]}```""")
        await ctx.send(f"""```{portfolio_complete[1]}```""")
    if not portfolio_complete:
        await ctx.send(Embedder.error(""))


@portfolio.error
async def portfolio_error(ctx, error: Exception):
    if isinstance(error, commands.BadArgument):
        msg = "Bad argument;\n`!portfolio [m or mobile (for mobile view)]`"
    elif isinstance(error, NoPositionsException):
        msg = "No position was found with the user!\nTry `!buy` command first to add positions."
    else:
        msg = uncaught(error)
    await ctx.send(embed=Embedder.error(msg))


# TODO: this doesn't work for now
# @bot.command(
#     help="Requires two arguments, ticker and price. Example !alert TSLA 800",
#     brief="Directly messages the user when the price hits the threshold indicated so they can buy/sell."
# )
# async def alert(ctx, ticker, price):
#     if float(live_stock_price(ticker) > float(price)):
#         while True:
#             print(live_stock_price(ticker))
#             if float(live_stock_price(ticker)) <= float(price):
#                 await ctx.author.send("```" + str(ticker).upper() + " has hit your price point of $" + price + ".```")
#                 break
#             await asyncio.sleep(10)
#     else:
#         while True:
#             if float(live_stock_price(ticker)) >= float(price):
#                 await ctx.author.send("```" + str(ticker).upper() + " has hit your price point of $" + price + ".```")
#                 break
#             await asyncio.sleep(10)


# @alert.error # TODO: doesn't work for now
# async def alert_error(ctx, error):
#     if isinstance(error, commands.CommandError):
#         msg = 'Came across an error while processing your request. Please check your ticker again.'
#     else:
#         msg = uncaught(error)
#     await ctx.send(embed=Embedder.error(msg))


@bot.event
async def on_command_error(ctx, error: Exception):
    if isinstance(error, commands.CommandNotFound):
        return await ctx.send(embed=Embedder.error("Command does not exist."))
    elif hasattr(ctx.command, "on_error"):
        return
    else:
        msg = uncaught(error)
    return await ctx.send(embed=Embedder.error(msg))


@bot.event
async def on_ready():
    sentry_sdk.init(
        SENTRY_DSN,
        traces_sample_rate=1.0
    )
    connect(DATABASE_URL)
    print("We are online!")
    print("Name: {}".format(bot.user.name))
    print("ID: {}".format(bot.user.id))

bot.run(TOKEN)
