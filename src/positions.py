import src.database as db
import discord
from src.functions import get_live_price
from tabulate import tabulate
from forex_python.converter import CurrencyRates


def sell_position(session, user_id: str, username: str, symbol: str, amount: int, price: float):
    # TODO: incorporate price, and maybe add cash attr for users
    try:
        symbol = get_symbol_or_create(session, symbol)
        symbol_id = symbol[0].symbol_id
        user = get_user_or_create(session, user_id=user_id, username=username)
        user_id = user[0].id
        existing = get_existing_position(session=session, user_id=user_id, symbol_id=symbol_id)
        if existing:
            ex_total, ex_amount = existing.total_price, existing.amount
            if ex_amount < amount:
                return False
            elif ex_amount == amount:
                session.delete(existing)
                return True
            new_amount = ex_amount - amount
            existing.total_price = ex_total - price * new_amount
            existing.amount = new_amount
            return True
        else:
            return False
    finally:
        session.commit()
        session.close()


def buy_position(session, user_id: str, username: str, symbol: str, amount: int, price: float, is_usd: bool):
    try:
        symbol = get_symbol_or_create(session, symbol)
        symbol_id = symbol[0].symbol_id
        user = get_user_or_create(session, user_id=user_id, username=username)
        user_id = user[0].id
        ex_total, ex_amount = 0, 0
        existing = get_existing_position(session=session, user_id=user_id, symbol_id=symbol_id)
        if existing:
            ex_total, ex_amount = existing.total_price, existing.amount
        new_total_price = float(ex_total + price * amount)
        new_amount = ex_amount + amount
        new_average_price = new_total_price / new_amount
        if existing:
            existing.total_price = new_total_price
            existing.amount = new_amount
            existing.average_price = new_average_price
        else:
            position_row = db.Positions(user_id=user_id, symbol_id=symbol_id,
                                        total_price=new_total_price, average_price=new_average_price,
                                        amount=new_amount, is_usd=is_usd)
            session.add(position_row)
        return True
    finally:
        session.commit()
        session.close()


def get_portfolio(session, user_id: str, username: str, mobile: bool):
    try:
        user = get_user_or_create(session=session, user_id=user_id, username=username)
        user_id = user[0].id
        positions = session.query(db.Positions).filter_by(user_id=user_id).all()
        portfolio = discord.Embed(title=f"{username}'s Portfolio", colour=discord.Colour.green()) if mobile else []
        portfolio_total_usd = 0
        portfolio_total_cad = 0
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
            if is_usd:
                portfolio_total_usd += current_total_price
            else:
                portfolio_total_cad += current_total_price
            pl = live_total_price - original_total_price
            pl_percent = ((live_price - average_price) / average_price) * 100
            positive = "+" if pl > 0 else ""
            pl = positive + neg_zero_handler(format(pl, '.2f'))
            pl_percent = positive + f"{neg_zero_handler(format(pl_percent, '.2f'))}%"
            average_price = format(average_price, '.2f')
            current_total_price = format(current_total_price, '.2f')
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
        total_in_usd = format(portfolio_total_usd + convert("CAD", "USD", portfolio_total_cad), '.2f')
        total_in_cad = format(convert("USD", "CAD", portfolio_total_usd) + portfolio_total_cad, '.2f')
        portfolio_total_usd = format(portfolio_total_usd, '.2f')
        portfolio_total_cad = format(portfolio_total_cad, '.2f')
        portfolio_total = [[portfolio_total_usd,
                            portfolio_total_cad,
                            total_in_usd,
                            total_in_cad]]
        if mobile:
            portfolio_total_mobile = discord.Embed(title=f"{username}'s Portfolio Summary",
                                                   colour=discord.Colour.green())
            portfolio_total_mobile.add_field(name="Total USD", value=portfolio_total_usd)
            portfolio_total_mobile.add_field(name="Total CAD", value=portfolio_total_cad)
            portfolio_total_mobile.add_field(name="Total in USD", value=total_in_usd)
            portfolio_total_mobile.add_field(name="Total in CAD", value=total_in_cad)
            return portfolio, portfolio_total_mobile

        else:
            portfolio_table = tabulate(portfolio,
                                       headers=["Symbol", "Amount", "Average", "Total", "P/L (%)", "Currency"],
                                       disable_numparse=True)
            portfolio_total_table = tabulate(portfolio_total,
                                             headers=["Total USD", "Total CAD", "Total in USD", "Total in CAD"],
                                             disable_numparse=True)
            return portfolio_table, portfolio_total_table
    finally:
        session.close()


def get_symbol_or_create(session, symbol: str):
    symbol_default = {"symbol": symbol}
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
