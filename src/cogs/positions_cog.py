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
        try:
            bought_price, currency = buy_position(user_id=user_id, username=username,
                                                  symbol=ticker, amount=amount,
                                                  price=price)
        except NotAmerican:
            return await ctx.send(embed=Embedder.error("Currently USD and CAD stocks are supported"))
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
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = "Missing arguments;\n`!buy [ticker (KBO)] [amount (13)] [price (12.50)(optional)]`"
        else:
            msg = uncaught(error)
        await ctx.send(embed=Embedder.error(msg))

    @commands.command()
    async def sell(self, ctx, ticker: str, amount: int, price: float = None):
        user_id = str(ctx.message.author.id)
        username = ctx.message.author.name
        ticker = ticker.upper()
        try:
            sold_price, currency = sell_position(user_id=user_id, username=username,
                                                 symbol=ticker, amount=amount, price=price)
        except NotAmerican:
            return await ctx.send(embed=Embedder.error("Currently USD and CAD stocks are supported"))
        total = sold_price * amount
        embed = Embedder.embed(title=f"Successfully Sold ${ticker}",
                               message=f"{ticker} x {amount} @{format(sold_price, '.2f')} {currency}\n"
                                       f"`Total: ${format(total, '.2f')} {currency}`")
        await ctx.send(embed=embed)

    @sell.error
    async def sell_error(self, ctx, error: Exception):
        if isinstance(error, commands.BadArgument):
            msg = "Bad argument;\n`!sell [ticker (KBO)] [amount (13)] [price (12.50)]`"
        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, NotEnoughPositionsToSell):
                msg = "You don't have enough positions to sell!"
            else:
                msg = uncaught(error.original)
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