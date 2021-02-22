import os
from dotenv import load_dotenv
from yahoo_fin.stock_info import *
import discord

suffixes = ['.V', '.TO', '.NE']
load_dotenv()
token = os.getenv("RAPID-API-KEY")


def live_stock_price(ticker):
    """
    :param ticker: str (the ticker of the stock you are looking for)
    :return: datatype: numpy-float64 (the price of the ticker)
    """
    return round(get_live_price(ticker), 2)


def getNews(ticker):
    """
    :param ticker: str (the ticker of the stock you are looking for)
    :return: res: dict (where the dictionary contains the summaries and links)
             titles: list (list of titles)
    """

    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/get-news"

    querystring = {"category": ticker}

    headers = {
        'x-rapidapi-key': token,
        'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)
    # Transform the data into json so we can fetch the data we need easily.
    data = response.json()
    # The data we need is under the key result, but item is also a key to result.
    news_json = data['items']['result']
    # If the fetched results are empty, that means the data has to be invalid.
    if len(news_json) == 0:
        raise Exception("Invalid Entry, please try again.")

    # The things that matter here are the links, summaries and the titles of the news articles.
    # So we go through news_json to get the corresponding values and append them to a list.
    # Limit the articles to 5.
    links = []
    summaries = []
    titles = []
    for key in news_json:
        # If there are 2048 characters in a message, Discord can't show it so we have to check that.
        # We just skip that article and go to the next article in the json.
        if key['summary'] and len(key['summary']) > 2048:
            continue
        if key['summary'] and len(key['summary']) < 2048:
            summaries.append(key['summary'])
        if key['link']:
            links.append(key['link'])
        if key['title']:
            titles.append(key['title'])
        if len(links) == 5:
            break

    # Turn the two lists into a hash and then return titles and res.
    res = dict(zip(summaries, links))
    return res, titles


def getMovers():
    """
    :return: Embedded details on the top 6 gainers, losers and volume in the US for the day.
    """
    day_gainers = {}
    day_losers = {}
    top_volume = {}
    for k, v in get_day_gainers().to_dict().items():
        if k in ['Name', 'Symbol', 'Price (Intraday)', 'Change', '% Change']:
            day_gainers[k] = v
        if len(day_gainers) == 5:
            break

    for k, v in get_day_losers().to_dict().items():
        if k in ['Name', 'Symbol', 'Price (Intraday)', 'Change', '% Change']:
            day_losers[k] = v
        if len(day_losers) == 5:
            break

    for k, v in get_day_most_active().to_dict().items():
        if k in ['Name', 'Symbol', 'Price (Intraday)', 'Change', '% Change', 'Volume']:
            top_volume[k] = v
        if len(top_volume) == 6:
            break

    gainers = discord.Embed(title="Day Gainers:", colour=discord.Colour.green())
    for i in range(0, 6):
        gainers.add_field(name=f"**{day_gainers['Name'][i]}**",
                          value=f"> Ticker: {day_gainers['Symbol'][i]}\n"
                                f"> Price: ${day_gainers['Price (Intraday)'][i]}\n"
                                f"> Change: +{day_gainers['Change'][i]}\n"
                                f"> % Change: +{round(day_gainers['% Change'][i], 2)}%\n")

    losers = discord.Embed(title="Day Losers:", colour=discord.Colour.red())
    for i in range(0, 6):
        losers.add_field(name=f"**{day_losers['Name'][i]}**",
                         value=f"> Ticker: {day_losers['Symbol'][i]}\n"
                               f"> Price: ${day_losers['Price (Intraday)'][i]}\n"
                               f"> Change: {day_losers['Change'][i]}\n"
                               f"> % Change: {round(day_losers['% Change'][i], 2)}%\n")

    volume = discord.Embed(title="Top Volume:")
    for i in range(0, 6):
        volume.add_field(name=f"**{top_volume['Name'][i]}**",
                         value=f"> Ticker: {top_volume['Symbol'][i]}\n"
                               f"> Price: ${top_volume['Price (Intraday)'][i]}\n"
                               f"> Change: {top_volume['Change'][i]}\n"
                               f"> % Change: {round(top_volume['% Change'][i], 2)}%\n"
                               f"> Volume: {humanize_number(top_volume['Volume'][i], 1)}\n")

    return gainers, losers, volume


def getDetails(ticker, region):
    """
    :param ticker: str (the ticker of the stock you are looking for)
    :param region: str (the regions, the valid regions are: US|BR|AU|CA|FR|DE|HK|IN|IT|ES|GB|SG)
    :return: stock_details: dict (the relevant details about the stock)
             name: str (the full name of the stock)
    """

    # Yahoo Finance requires Canadian stocks to have .TO at the end of the ticker e.g.
    # SU.TO. So we automatically add .TO to the ticker if the region set is CA.
    if region.upper() == "CA":
        if ('.V' in ticker.upper()) or ('.NE' in ticker.upper()) or ('.TO' in ticker.upper()):
            pass
        else:
            price, suffix = findSuffix(ticker)
            ticker = ticker + suffix

    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/v2/get-summary"
    querystring = {"symbol": ticker, "region": region}
    headers = {
        'x-rapidapi-key': token,
        'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com"
    }
    response = requests.request("GET", url, headers=headers, params=querystring)
    # Grab the response and turn it into json format.
    data = response.json()
    # Grabbing all the data within key price.
    priceKey = data["price"]
    # Assigning all the variables to the corresponding data that we need.
    opening_price = priceKey["regularMarketOpen"]["fmt"]
    curr_price = priceKey["regularMarketPrice"]["fmt"]
    day_high = priceKey["regularMarketDayHigh"]["fmt"]
    day_low = priceKey["regularMarketDayLow"]["fmt"]
    percent_change = priceKey["regularMarketChangePercent"]["fmt"]
    volume_today = priceKey["regularMarketVolume"]["fmt"]
    mkt_cap = priceKey["marketCap"]["fmt"]
    name = priceKey["longName"]
    # currency = data["earnings"]["financialCurrency"]

    # Grab the necessary data within summaryDetail, so 52 week high, 52 week low and potential dividends.
    summaryDetail = data["summaryDetail"]
    fifty_two_week_high = summaryDetail["fiftyTwoWeekHigh"]["fmt"]
    fifty_two_week_low = summaryDetail["fiftyTwoWeekLow"]["fmt"]

    # Place the details in a hash so we can iterate through it so we can put it into something.
    stock_details = {'Opening Price': opening_price, 'Current Price': curr_price, 'Day High': day_high,
                     'Day Low': day_low, 'Percent Change': percent_change, 'Volume': volume_today,
                     'Mkt Cap': mkt_cap, '52 Week High': fifty_two_week_high, '52 Week Low': fifty_two_week_low}

    # Not all stocks have dividends, so we have to consider that case.
    if len(summaryDetail["trailingAnnualDividendYield"]) == 0:
        return stock_details, name

    # Otherwise we grab the dividend data as well.
    else:
        annual_div_yield = summaryDetail["trailingAnnualDividendYield"]["fmt"]
        annual_div_rate = summaryDetail["trailingAnnualDividendRate"]["fmt"]
        div_date = summaryDetail["exDividendDate"]["fmt"]
        stock_details['Annual Div Yield'] = annual_div_yield
        stock_details['Annual Div Rate'] = annual_div_rate
        stock_details['Div Date'] = div_date

        return stock_details, name


def getHistoricalData(ticker, region, days):
    """
    :param ticker: str (the ticker of the stock you are looking for)
    :param region: str (the region where the stock is traded)
    :param days: int (the number of days to compare the current stock price to)
    :return: tuple<float, float> (Value of difference between days in numerical and percentage representation)
    """
    # Yahoo Finance requires Canadian stocks to have .TO at the end of the ticker e.g.
    # SU.TO. So we automatically add .TO to the ticker if the region set is CA.
    if region.upper() == "CA":
        if ('.V' in ticker.upper()) or ('.NE' in ticker.upper()) or ('.TO' in ticker.upper()):
            pass
        else:
            price, suffix = findSuffix(ticker)
            ticker = ticker + suffix

    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/v3/get-historical-data"

    querystring = {"symbol": ticker, "region": region}

    headers = {
        'x-rapidapi-key': token,
        'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com",
    }

    # TODO: get stock's historical date so we don't have a null value - number of days could exceed the stock's age somehow
    if int(days) > 200:
        raise Exception("Value exceeds maximum number of days (200). Please enter a smaller value.")
    elif int(days) < 1:
        raise Exception("Invalid Entry. Value must be between 1 and 200. Please try again.")

    response = requests.request("GET", url, headers=headers, params=querystring)
    # Transform the data into json so we can fetch the data we need easily.
    data = response.json()

    if len(data['prices']) < int(days):
        raise Exception("Invalid Entry. The stock may not have data available for this time period. Please try again.")
    
    # We get the data from prices on the given amount of days wanted from historical data
    historicalData = data['prices'][int(days)]

    # If the fetched results are empty, that means the data has to be invalid.
    if len(historicalData) == 0:
        raise Exception("Invalid Entry. The stock may not have data available for this time period. Please try again.")

    current_data = get_live_price(ticker)

    # Compare both data points and derive a monetary difference between the two in number and percentage values.
    amountDiffNumerical = float(current_data) - float(historicalData['close'])
    amountDiffPercentage = (amountDiffNumerical / float(historicalData['close'])) * 100

    if is_cad(ticker):
        currency = 'CAD'
    else:
        currency = 'USD'

    stock_details = {
        'PriceChange': round(amountDiffNumerical, 2),
        'PriceChangePercentage': round(amountDiffPercentage, 2),
        'Currency': currency
    }

    return stock_details


# Recursively tries to find the associated suffix
# for the corresponding stock in the TSX.
def findSuffix(ticker, i=0):
    try:
        live_stock_price(ticker + suffixes[i])
    except AssertionError or KeyError:
        i = i + 1
        if i > 3:
            raise Exception
        return findSuffix(ticker, i)
    else:
        return live_stock_price(ticker + suffixes[i]), suffixes[i]


def is_cad(text):
    return any([('.V' in text.upper()), ('.NE' in text.upper()), ('.TO' in text.upper())])


def calculate_total(ticker: str, amount: int, price: float = None):
    ticker = ticker.upper()
    currency = "CAD" if is_cad(ticker) else "USD"
    live_price = live_stock_price(ticker)
    if live_price:
        ticker_price = price if price else live_price
        total = ticker_price * amount
        return ticker_price, total, currency


def humanize_number(value, fraction_point=1):
    powers = [10 ** x for x in (12, 9, 6, 3, 0)]
    human_powers = ('T', 'B', 'M', 'K', '')
    is_negative = False
    if not isinstance(value, float):
        value = float(value)
    if value < 0:
        is_negative = True
        value = abs(value)
    for i, p in enumerate(powers):
        if value >= p:
            return_value = str(round(value / (p / (10.0 ** fraction_point))) /
                               (10 ** fraction_point)) + human_powers[i]
            break
    if is_negative:
        return_value = "-" + return_value

    return return_value
