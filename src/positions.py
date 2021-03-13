import src.database as db
import discord
from financelite import Stock
from src.database import Session
from discord.ext import commands
from src.functions import get_live_price
from tabulate import tabulate
from forex_python.converter import CurrencyRates


class NotEnoughPositionsToSell(Exception):
    pass


def sell_position(user_id: str, username: str, symbol: str, amount: int, price: float):
    # TODO: maybe add cash attr for users
    session = Session()
    try:
        sold_price, currency = Stock(symbol).get_live()
        sold_price = price if price else sold_price
        symbol = get_symbol_or_create(session, symbol, currency)
        symbol_id = symbol[0].symbol_id
        user = get_user_or_create(session, user_id=user_id, username=username)
        user_id = user[0].id
        existing = get_existing_position(session=session, user_id=user_id, symbol_id=symbol_id)
        if existing:
            ex_total, ex_amount = existing.total_price, existing.amount
            if ex_amount < amount:
                raise NotEnoughPositionsToSell
            elif ex_amount == amount:
                session.delete(existing)
                return sold_price, currency
            new_amount = ex_amount - amount
            existing.total_price = ex_total - sold_price * new_amount
            existing.amount = new_amount
            return sold_price, currency
        else:
            raise NotEnoughPositionsToSell
    finally:
        session.commit()
        session.close()


def buy_position(user_id: str, username: str, symbol: str, amount: int, price: float):
    session = Session()
    bought_price, currency = Stock(ticker=symbol).get_live()
    bought_price = price if price else bought_price
    try:
        symbol = get_symbol_or_create(session, symbol, currency)
        symbol_id = symbol[0].symbol_id
        user = get_user_or_create(session, user_id=user_id, username=username)
        user_id = user[0].id
        ex_total, ex_amount = 0, 0
        existing = get_existing_position(session=session, user_id=user_id, symbol_id=symbol_id)
        if existing:
            ex_total, ex_amount = existing.total_price, existing.amount
        new_total_price = float(ex_total + bought_price * amount)
        new_amount = ex_amount + amount
        new_average_price = new_total_price / new_amount
        if existing:
            existing.total_price = new_total_price
            existing.amount = new_amount
            existing.average_price = new_average_price
        else:
            position_row = db.Positions(user_id=user_id, symbol_id=symbol_id,
                                        total_price=new_total_price, average_price=new_average_price,
                                        amount=new_amount)
            session.add(position_row)
        return bought_price, currency
    finally:
        session.commit()
        session.close()


def get_portfolio(session, user_id: str, username: str, mobile: bool):
    try:
        user = get_user_or_create(session=session, user_id=user_id, username=username)
        user_id = user[0].id
        positions = session.query(db.Positions).filter_by(user_id=user_id).all()
        if not positions:
            raise NoPositionsException
        portfolio = discord.Embed(title=f"{username}'s Portfolio", colour=discord.Colour.green()) if mobile else []
        portfolio_total_usd = 0
        portfolio_total_cad = 0
        average_total_usd = 0
        average_total_cad = 0
        for pos in positions:
            symbol_id = pos.symbol_id
            symbol = session.query(db.Symbols).filter_by(symbol_id=symbol_id).one().symbol
            is_usd = pos.is_usd
            currency = "USD" if is_usd else "CAD"
            amount = pos.amount
            average_price = pos.average_price
            live_price = get_live_price(symbol)
            live_total_price = amount * live_price
            original_total_price = pos.total_price
            current_total_price = live_price * amount
            pl = live_total_price - original_total_price
            pl_percent = ((live_price - average_price) / average_price) * 100
            if is_usd:
                portfolio_total_usd += current_total_price
                average_total_usd += average_price * amount
            else:
                portfolio_total_cad += current_total_price
                average_total_cad += average_price * amount
            positive = "+" if pl > 0 else ""
            pl = positive + neg_zero_handler(two_decimal(pl))
            pl_percent = positive + f"{neg_zero_handler(two_decimal(pl_percent))}%"
            average_price = two_decimal(average_price)
            current_total_price = two_decimal(current_total_price)
            if mobile:
                portfolio.add_field(name=f"**{symbol}**",
                                    value=f"> Amount: {amount}\n"
                                          f"> Average Price: {average_price}\n"
                                          f"> Total: {current_total_price}\n"
                                          f"> P/L (%): {pl} ({pl_percent})\n"
                                          f"> Currency: {currency}")
            else:
                portfolio.append([symbol,
                                  f"x {amount}",
                                  average_price,
                                  current_total_price,
                                  f"{pl} ({pl_percent})",
                                  currency])
        total_in_usd, total_in_cad = get_total_usd_cad(portfolio_total_usd, portfolio_total_cad)
        original_in_usd, original_in_cad = get_total_usd_cad(average_total_usd, average_total_cad)
        pl_usd = total_in_usd - original_in_usd
        pl_cad = total_in_cad - original_in_cad
        pl_percent_in_usd = two_decimal((pl_usd / original_in_usd) * 100)
        pl_percent_in_cad = two_decimal((pl_cad / original_in_cad) * 100)
        portfolio_total_usd = two_decimal(portfolio_total_usd)
        portfolio_total_cad = two_decimal(portfolio_total_cad)
        positive = "+" if pl_usd > 0 or pl_cad > 0 else ""
        portfolio_total = [[portfolio_total_usd,
                            portfolio_total_cad,
                            two_decimal(total_in_usd),
                            two_decimal(total_in_cad),
                            f"{positive}{two_decimal(pl_usd)} ({positive}{pl_percent_in_usd}%)",
                            f"{positive}{two_decimal(pl_cad)} ({positive}{pl_percent_in_cad}%)"
                            ]]
        if mobile:
            portfolio_total_mobile = discord.Embed(title=f"{username}'s Portfolio Summary",
                                                   colour=discord.Colour.green())
            portfolio_total_mobile.add_field(name="Total USD", value=portfolio_total_usd)
            portfolio_total_mobile.add_field(name="Total CAD", value=portfolio_total_cad)
            portfolio_total_mobile.add_field(name="Total in USD", value=two_decimal(total_in_usd))
            portfolio_total_mobile.add_field(name="Total in CAD", value=two_decimal(total_in_cad))
            portfolio_total_mobile.add_field(name="P/L in USD",
                                             value=f"{positive}{two_decimal(pl_usd)} ({positive}{pl_percent_in_usd}%)")
            portfolio_total_mobile.add_field(name="P/L in CAD",
                                             value=f"{positive}{two_decimal(pl_cad)} ({positive}{pl_percent_in_cad}%)")

            return portfolio, portfolio_total_mobile

        else:
            portfolio_table = tabulate(portfolio,
                                       headers=["Symbol", "Amount", "Average", "Total", "P/L (%)", "Currency"],
                                       disable_numparse=True)
            portfolio_total_table = tabulate(portfolio_total,
                                             headers=["Total USD", "Total CAD", "Total in USD", "Total in CAD",
                                                      "P/L in USD", "P/L in CAD"],
                                             disable_numparse=True)
            return portfolio_table, portfolio_total_table
    finally:
        session.close()


def get_symbol_or_create(session, symbol: str, currency: str):
    symbol_default = {"symbol": symbol.upper(), "currency": currency}
    return db.get_or_create(session=session, model=db.Symbols, defaults=symbol_default, symbol=symbol)


def get_user_or_create(session, user_id: str, username: str):
    user_default = {"user_id": f"{user_id}", "username": username}
    return db.get_or_create(session=session, model=db.Users, defaults=user_default, user_id=user_id, username=username)


def get_existing_position(session, user_id, symbol_id: int):
    existing = session.query(db.Positions).filter_by(user_id=user_id, symbol_id=symbol_id).first()
    return existing


def convert(initial, final, amount):
    return CurrencyRates().convert(base_cur=initial, dest_cur=final, amount=amount)


def neg_zero_handler(neg_zero):
    return "0.00" if neg_zero == "-0.00" else neg_zero


def two_decimal(number: float):
    return format(number, '.2f')


def get_total_usd_cad(usd, cad):
    total_in_usd = usd + convert("CAD", "USD", cad)
    total_in_cad = cad + convert("USD", "CAD", usd)
    return total_in_usd, total_in_cad


class NoPositionsException(commands.CommandError):
    pass
