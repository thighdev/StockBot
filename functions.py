import requests
import os
from dotenv import load_dotenv
from yahoo_fin.stock_info import *


suffixes = ['.V', '.TO', '.NE']
load_dotenv()
token = os.getenv("RAPID-API-KEY")


def live_stock_price(ticker):
    """
    :param ticker: str (the ticker of the stock you are looking for)
    :return: datatype: numpy-float64 (the price of the ticker)
    """
    return round(get_live_price(ticker), 2)


def getMovers():
    """
    :return: titles: list (list of titles that represent the top gainers, top losers and top volume in US)
             symbols_top_volume, symbols_top_losers, symbols_top_volume: dicts
             (dict of the top gainers, top losers and top volume for the day)
    """

    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/market/v2/get-movers"

    querystring = {"region": "US", "lang": "en-US", "start": "0", "count": "6"}

    headers = {
        'x-rapidapi-key': token,
        'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)
    data = response.json()
    # print(data)
    # print(data['finance']['result'])

    titles = []
    for i in range(3):
        titles.append(data['finance']['result'][i]['title'])

    # Hash the symbols by the keys (which will be indicated by the rank)
    top_gainers = data['finance']['result'][0]['quotes']
    symbols_top_gainers = {}
    #print(top_gainers[0]['symbol'])
    for i in range(0, 6):
        symbols_top_gainers[i + 1] = top_gainers[i]['symbol']



    # Hash the symbols by the keys (which will be indicated by the rank)
    top_losers = data['finance']['result'][1]['quotes']
    symbols_top_losers = {}
    for i in range(0, 6):
        symbols_top_losers[i + 1] = top_losers[i]['symbol']

    # print(symbols_top_losers)
    # Hash the symbols by the keys (which will be indicated by the rank)
    top_volume = data['finance']['result'][2]['quotes']
    symbols_top_volume = {}
    for i in range(0, 6):
        symbols_top_volume[i + 1] = top_volume[i]['symbol']

    # print(symbols_top_volume)

    return titles, symbols_top_gainers, symbols_top_losers, symbols_top_volume


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
    :param days: int (the number of days to compare the current stock price to)
    :return: dict (stock name with info relating to historical comparison based on given amount of days)
    """
    # Yahoo Finance requires Canadian stocks to have .TO at the end of the ticker e.g.
    # SU.TO. So we automatically add .TO to the ticker if the region set is CA.
    if region.upper() == "CA":
        if ('.V' in ticker.upper()) or ('.NE' in ticker.upper()) or ('.TO' in ticker.upper()):
            pass
        else:
            price, suffix = findSuffix(ticker)
            ticker = ticker + suffix

    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/get-news"

    querystring = {"symbol": ticker, "region": region}

    headers = {
        'x-rapidapi-key': token,
        'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com",
        "useQueryString": true
    }

    #TODO: get stock's historical date so we don't have a null value - number of days could exceed the stock's age somehow
    if days > 200:
        raise Exception("Value exceeds maximum number of days (200). Please enter a smaller value.")
    elif days < 1:
        raise Exception("Invalid Entry. Value must be between 1 and 200. Please try again.")

    response = requests.request("GET", url, headers=headers, params=querystring)
    # Transform the data into json so we can fetch the data we need easily.
    data = response.json()
    # We get the data from prices on the given amount of days wanted from historical data
    historicalData = data['prices'][days]

    # If the fetched results are empty, that means the data has to be invalid.
    if len(historicalData) == 0:
        raise Exception("Invalid Entry, please try again.")

    current_data = getDetails(ticker, region)

    # Compare both data points and derive a monetary difference between the two in number and percentage values.
    amountDiffNumerical = current_data['Current Price'] - historicalData['close']
    amountDiffPercentage = 0

    if amountDiffNumerical < 0:
        # If the current value is lower than the historical data, we negate the ratio since it's a negative percentage drop.
        amountDiffPercentage = -(historicalData['close'] / current_data['Current Price'])
    else:
        amountDiffPercentage = current_data['Current Price'] / historicalData['close']

    return amountDiffNumerical, amountDiffPercentage

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
