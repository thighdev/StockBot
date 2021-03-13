from discord.ext import commands
from src.util.SentryHelper import uncaught
from src.util.Embedder import Embedder
from src.positions import *
from src.functions import *
from src.database import Session


class Positions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def buy(self, ctx, ticker: str, amount: int, price: float = None):
        user_id = str(ctx.message.author.id)
        username = ctx.message.author.name
        ticker = ticker.upper()
        bought_price, currency = buy_position(user_id=user_id, username=username,
                                              symbol=ticker, amount=amount,
                                              price=price)
        if bought_price:
            total = bought_price * amount
            embed = Embedder.embed(title=f"Successfully bought {ticker}",
                                   message=f"{ticker} x {amount} @{format(bought_price, '.2f')} {currency}\n"
                                           f"`Total: ${format(total, '.2f')} {currency}`")
        else:
            embed = Embedder.error("Something went wrong.")
        await ctx.send(embed=embed)

    @buy.error
    async def buy_error(self, ctx, error: Exception):
        if isinstance(error, commands.BadArgument):
            msg = "Bad argument;\n`!buy [ticker (KBO)] [amount (13)] [price (12.50)(optional)]`"
        elif isinstance(error, commands.CommandInvokeError):
            msg = "Invalid ticker."
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = "Missing arguments;\n`!buy [ticker (KBO)] [amount (13)] [price (12.50)(optional)]`"
        else:
            msg = uncaught(error)
        await ctx.send(embed=Embedder.error(msg))

    @commands.command()
    async def sell(self, ctx, ticker: str, amount: int, price: float = None):
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
    async def sell_error(self, ctx, error: Exception):
        if isinstance(error, commands.BadArgument):
            msg = "Bad argument;\n`!sell [ticker (KBO)] [amount (13)] [price (12.50)]`"
        elif isinstance(error, commands.CommandInvokeError):
            msg = "Invalid ticker."
        else:
            msg = uncaught(error)
        await ctx.send(embed=Embedder.error(msg))

    @commands.command()
    async def portfolio(self, ctx, mobile: str = ""):
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
    async def portfolio_error(self, ctx, error: Exception):
        if isinstance(error, commands.BadArgument):
            msg = "Bad argument;\n`!portfolio [m or mobile (for mobile view)]`"
        elif isinstance(error, NoPositionsException):
            msg = "No position was found with the user!\nTry `!buy` command first to add positions."
        else:
            msg = uncaught(error)
        await ctx.send(embed=Embedder.error(msg))