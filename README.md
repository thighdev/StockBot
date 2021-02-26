# StockBot
## Introduction
StockBot is a self-hostable [Discord bot](https://discordpy.readthedocs.io/en/latest/index.html) that provides various informations regarding stocks.  
`Python 3` and `MySQL` are required to run the bot.  
Optionally, you may choose to run the bot using [Docker](https://www.docker.com/) and docker-compose.  

## Configuration, Installation, and Execution
StockBot uses `.env` file to configure environmental variables. This file needs to exist in the root directory with correct environment variables for the bot to run.  
Create a `.env` file in the root directory and configure like following:
```
TOKEN=bot-token-here
RAPID-API-KEY=rapid-api-key-here
DATABASE_URL=database-url-here
SENTRY_DSN=sentry-here
```
To install, run `git clone https://github.com/thaixnguyen/StockBot.git`  
To run the bot, run `python stockbot.py`

### Docker
Docker and docker-compose makes running the bot extremely simple.  
First, configure your `.env` file as mentioned before, but with `DATABASE_URL=mysql+pymysql://root:root@mysql/stockbot?charset=utf8mb4`.  
This is the MySQL container's database URL.  
#### To run the bot in a Linux environment, install [PyInvoke](http://www.pyinvoke.org/), and proceed:
  1. `invoke build` - you only need to run this once.
  2. `invoke dev`  

That's it!  

#### To run the bot in a Windows environemnt:
1. `docker-compose -f docker/docker-compose.yml build` - you only need to run this once.
2. `docker-compose -f docker/docker-compose.yml up -d`  
* If you are using CMD or PowerShell:  
3. `docker-compose -f docker/docker-compose.yml exec stockbot python /apps/stockbot/stockbot.py`  
* If you are using mintty or gitbash:  
3. `winpty docker-compose -f docker/docker-compose.yml exec stockbot python //apps//stockbot//stockbot.py`


## Commands
Currently, StockBot uses the prefix `!` to invoke commands.  
**(required) [optional]**

#### `!movers`
Returns the top gainers, losers, and volumes traded from the US  

#### `!info (ticker) [region]`  
Returns a market summary of the specified ticker. Regions are `[US, CA]` currently.  

#### `!news (ticker)`
Returns recent news related to the specified ticker.  

#### `!live (ticker)`
Returns the live price of the ticker.  

#### `!hist (ticker) [region] (days)`
Returns info regarding increase or decrease in stock price in the last x days  

#### `!alert (ticker) (price)`
Directly messages the user when the price hits the threshold indicated so they can buy/sell.  

#### `!buy (ticker) (amount) [price]`
Virtually buys a set amount of the stock. If price is not given, it will be the live price.  

#### `!sell (ticker) (amount) [price]`
Virtually sells a set amount of the stock. If price is not given, it will be the live price. 

#### `!portfolio [m | mobile]`
Returns the user's portfolio based on their `!buy` and `!sell` history. m or mobile argument will provide a mobile-friendly view

## Dev
Please visit [Dev](https://github.com/thaixnguyen/StockBot/blob/master/README.dev.md) for information.  
