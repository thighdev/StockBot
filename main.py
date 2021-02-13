import discord
from functions import *
from discord.ext import commands
from pretty_help import PrettyHelp
from dotenv import load_dotenv
import asyncio

bot = commands.Bot(command_prefix="!", help_command=PrettyHelp(no_category='Commands'))
load_dotenv()
token = os.getenv("TOKEN")


@bot.command(
    help="Requires no arguments, just checks for the top gainers, losses and volume in the US. e.g. !movers",
    brief="Returns the top gainers, losses and volume from the US.")
async def movers(ctx):
    titles, top_gainers, top_losers, top_volume = getMovers()
    embedtop = discord.Embed(title=titles[0])
    embedloser = discord.Embed(title=titles[1])
    embedvolume = discord.Embed(title=titles[2])

    for key, value in top_gainers.items():
        embedtop.add_field(name=key, value=value, inline=True)

    for key, value in top_losers.items():
        embedloser.add_field(name=key, value=value, inline=True)

    for key, value in top_volume.items():
        embedvolume.add_field(name=key, value=value, inline=True)

    await ctx.send(embed=embedtop)
    await ctx.send(embed=embedloser)
    await ctx.send(embed=embedvolume)


@bot.command(
    help="Requires two arguments, ticker and region. Default region used"
         " is US. Example of command: !info BB CA or !info TSLA",
    brief="Returns a market summary of the specified ticker.")
async def info(ctx, arg1, arg2='US'):
    keys = ['Opening Price', 'Current Price', 'Day High',
            'Day Low', '52 Week High', '52 Week Low']
    stock_details, name = getDetails(str(arg1), str(arg2))
    embed = discord.Embed(title="Information on " + name)
    if len(stock_details) == 9:
        for key, value in stock_details.items():
            if key in keys:
                embed.add_field(name=key, value="$" + value, inline=True)
                continue
            else:
                embed.add_field(name=key, value=value, inline=True)
        await ctx.send(embed=embed)

    else:
        for key, value in stock_details.items():
            if key in keys:
                embed.add_field(name=key, value="$" + value, inline=True)
                continue
            if key == 'Annual Div Rate':
                embed.add_field(name=key, value="$" + value + " per share", inline=True)
            else:
                embed.add_field(name=key, value=value, inline=True)
        await ctx.send(embed=embed)


@bot.command(
    help="Requires one argument, ticker. Example !news TSLA",
    brief="Returns recent news related to the specified ticker")
async def news(ctx, arg1, *args):
    res, titles = getNews(str(arg1))
    i = 0
    for key, value in res.items():
        embed = discord.Embed(title=str(titles[i]), url=str(value),
                              description=str(key),
                              color=discord.Color.blue())
        i += 1
        await ctx.send(embed=embed)


@bot.command(
    help="Requires one argument ticker and one optional argument region (specifically for Canada). Example !live TSLA "
         "or !live BB CA",
    brief="Returns the live price of the ticker")
async def live(ctx, arg1, *args):
    if len(args) == 1 and args[0].upper() == 'CA':
        if ('.V' in arg1.upper()) or ('.NE' in arg1.upper()) or ('.TO' in arg1.upper()):
            price = live_stock_price(str(arg1))
            response = '```The current price of ' + str(arg1).upper() + ' is $' + str(price) + ' CAD.```'
            await ctx.send(response)
        else:
            price, suffix = findSuffix(str(arg1))
            response = '```The current price of ' + str(arg1).upper() + suffix + ' is $' + str(price) + ' CAD.```'
            await ctx.send(response)
    elif ('.V' in arg1.upper()) or ('.NE' in arg1.upper()) or ('.TO' in arg1.upper()):
        price = live_stock_price(str(arg1))
        response = '```The current price of ' + str(arg1).upper() + ' is $' + str(price) + ' CAD.```'
        await ctx.send(response)
    else:
        price = live_stock_price(str(arg1))
        response = '```The current price of ' + str(arg1).upper() + ' is $' + str(price) + ' USD.```'
        await ctx.send(response)

@bot.command(
    help="Requires one argument ticker and one optional argument region (specifically for Canada) and one argument number of days. Example !hist TSLA 45"
         "or !live BB CA 14",
    brief="Returns info regarding increase or decrease in stock price in the last x days")
async def historical(ctx, arg1, *args):
    if args[0].isdigit():
        # No region specified, default to US
        priceDiff, pricePercent = getHistoricalData(arg1, 'US', args[0])
        response = str(arg1.upper()) + ' performance in last ' + str(args[0]) + ' days: ' + str(priceDiff) + '(%' + str(pricePercent) + ')'
        await ctx.send(response)
    else:
        # Region is specified, so there should be 2 arguments: region and number of days
        priceDiff, pricePercent = getHistoricalData(arg1, args[0].upper(), args[1])
        response = str(arg1.upper()) + ' performance in last ' + str(args[1]) + ' days: ' + str(priceDiff) + '(%' + str(pricePercent) + ')'
        await ctx.send(response)

@bot.command(
    help="Requires two arguments, ticker and price. Example !alert TSLA 800",
    brief="Directly messages the user when the price hits the threshold indicated so they can buy/sell."
)
async def alert(ctx, ticker, price):
    if float(live_stock_price(ticker) > float(price)):
        while True:
            print(live_stock_price(ticker))
            if float(live_stock_price(ticker)) <= float(price):
                await ctx.author.send("```" + str(ticker).upper() + " has hit your price point of $" + price + ".```" )
                break
            await asyncio.sleep(10)
    else:
        while True:
            if float(live_stock_price(ticker)) >= float(price):
                await ctx.author.send("```" + str(ticker).upper() + " has hit your price point of $" + price + ".```")
                break
            await asyncio.sleep(10)


@info.error
async def info_error(ctx, error):
    if isinstance(error, commands.CommandError):
        await ctx.send('Came across an error while processing your request. '
                       'Check if your region corresponds to the proper exchange, '
                       'or re-check the ticker you used.')


@news.error
async def news_error(ctx, error):
    if isinstance(error, commands.CommandError):
        await ctx.send('Came across an error while processing your request.')


@live.error
async def live_error(ctx, error):
    if isinstance(error, commands.CommandError):
        await ctx.send('Came across an error while processing your request. '
                       'Check if your region corresponds to the proper exchange, '
                       'or re-check the ticker you used.')


@alert.error
async def alert_error(ctx, error):
    if isinstance(error, commands.CommandError):
        await ctx.send('Came across an error while processing your request. '
                       'Please check your ticker again.')


@bot.event
async def on_ready():
    print("We are online!")
    print("Name: {}".format(bot.user.name))
    print("ID: {}".format(bot.user.id))

bot.run(token)
