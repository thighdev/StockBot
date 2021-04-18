from src.functions import *
from discord.ext import commands
from pretty_help import PrettyHelp
from src.util.Embedder import *
from src.util.SentryHelper import uncaught
from src.database import connect
from src.cogs.positions_cog import Positions
from src.cogs.information_cog import Information
import sentry_sdk

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
SENTRY_DSN = os.getenv("SENTRY_DSN")
dev_prefix = os.getenv("DEV_PREFIX")
prefix = "!" if not dev_prefix else dev_prefix
bot = commands.Bot(
    command_prefix=prefix, help_command=PrettyHelp(no_category="Commands")
)


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
    sentry_sdk.init(SENTRY_DSN, traces_sample_rate=1.0)
    connect(DATABASE_URL)
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name=f"for prefix: {prefix}"
        )
    )
    print("We are online!")
    print("Name: {}".format(bot.user.name))
    print("ID: {}".format(bot.user.id))


bot.add_cog(Positions(bot))
bot.add_cog(Information(bot))
bot.run(TOKEN)
