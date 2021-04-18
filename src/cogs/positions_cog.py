from discord.ext import commands
from src.util.SentryHelper import uncaught
from src.util.Embedder import Embedder
from src.positions import *
from src.functions import *


class Positions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def buy(self, ctx, ticker: str, amount: int, price: float = None):
        user_id = str(ctx.message.author.id)
        username = ctx.message.author.name
        ticker = ticker.upper()
        try:
            bought_price, currency = buy_position(
                user_id=user_id,
                username=username,
                symbol=ticker,
                amount=amount,
                price=price,
            )
        except NotAmerican:
            return await ctx.send(
                embed=Embedder.error("Currently USD and CAD stocks are supported")
            )
        if bought_price:
            total = bought_price * amount
            embed = Embedder.embed(
                title=f"Successfully bought {ticker}",
                message=f"{ticker} x {amount} @{format(bought_price, '.2f')} {currency}\n"
                f"`Total: {format(total, '.2f')} {currency}`",
            )
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
            sold_price, currency = sell_position(
                user_id=user_id,
                username=username,
                symbol=ticker,
                amount=amount,
                price=price,
            )
        except NotAmerican:
            return await ctx.send(
                embed=Embedder.error("Currently USD and CAD stocks are supported")
            )
        total = sold_price * amount
        embed = Embedder.embed(
            title=f"Successfully Sold ${ticker}",
            message=f"{ticker} x {amount} @{format(sold_price, '.2f')} {currency}\n"
            f"`Total: {format(total, '.2f')} {currency}`",
        )
        await ctx.send(embed=embed)

    @sell.error
    async def sell_error(self, ctx, error: Exception):
        if isinstance(error, commands.BadArgument):
            msg = "Bad argument;\n`!sell [ticker (KBO)] [amount (13)] [price (12.50)]`"
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = "Missing arguments;\n`!sell [ticker (KBO)] [amount (13)] [price (12.50)(optional)]`"
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
        user_id = ctx.author.id
        username = ctx.author.name
        mobile = bool(mobile)
        portfolio, summary = get_portfolio(
            user_id=user_id, username=username, mobile=mobile
        )
        len_pf = len(portfolio)
        if mobile:
            await ctx.send(embed=portfolio)
            return await ctx.send(embed=summary)
        if len_pf > 1:
            message = await ctx.send(f"```diff\n{portfolio[0]}\n```")
            info_message = await ctx.send(f"`Page: 1/{len_pf}`")
            await ctx.send(f"```diff\n{summary}\n```")
            await info_message.add_reaction("⏮")
            await info_message.add_reaction("◀")
            await info_message.add_reaction("▶")
            await info_message.add_reaction("⏭")
            await info_message.add_reaction("❌")

            def check(reaction, user):
                return user == ctx.author

            def info_format(current):
                return f"`Page: {current}/{len_pf} (10 positions per page)"

            i = 0
            reaction = None

            while True:
                if str(reaction) == "⏮":
                    i = 0
                    await message.edit(content=f"```diff\n{portfolio[i]}\n```")
                    await info_message.edit(content=info_format(i))
                elif str(reaction) == "◀":
                    if i > 0:
                        i -= 1
                        await message.edit(content=f"```diff\n{portfolio[i]}\n```")
                        await info_message.edit(content=info_format(i))
                elif str(reaction) == "▶":
                    if i < len_pf - 1:
                        i += 1
                        await message.edit(content=f"```diff\n{portfolio[i]}\n```")
                        await info_message.edit(content=info_format(i))
                elif str(reaction) == "⏭":
                    i = -1
                    await message.edit(content=f"```diff\n{portfolio[i]}\n```")
                    await info_message.edit(content=info_format(len_pf))
                elif str(reaction) == "❌":
                    return await info_message.clear_reactions()
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add", timeout=30.0, check=check
                    )
                    await info_message.remove_reaction(reaction, user)
                except Exception:
                    break
            await info_message.delete()
        else:
            await ctx.send(f"```diff\n{portfolio[0]}\n```")
            await ctx.send(f"```diff\n{summary}\n```")

    @portfolio.error
    async def portfolio_error(self, ctx, error: Exception):
        if isinstance(error, commands.BadArgument):
            msg = "Bad argument;\n`!portfolio [m or mobile (for mobile view)]`"
        elif isinstance(error, NoPositionsException):
            msg = "No position was found with the user!\nTry `!buy` command first to add positions."
        else:
            msg = uncaught(error)
        await ctx.send(embed=Embedder.error(msg))
