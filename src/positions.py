import src.database as db
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
    except Exception as e:
        print(e)
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
        session.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        session.close()


def get_portfolio(session, user_id: str, username: str):
    try:
        user = get_user_or_create(session=session, user_id=user_id, username=username)
        user_id = user[0].id
        positions = session.query(db.Positions).filter_by(user_id=user_id).all()
        portfolio = []
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
            pl = live_total_price - current_total_price + 0
            pl_percent = ((live_price - average_price) / average_price) * 100
            positive = "+" if pl > 0 else ""
            portfolio.append([symbol,
                              f"x {amount}",
                              format(average_price, '.2f'),
                              format(current_total_price, '.2f'),
                              positive + format(current_total_price - original_total_price, '.2f'),
                              positive + f"{format(pl_percent, '.2f')}%",
                              currency])
        total_in_usd = portfolio_total_usd + convert("CAD", "USD", portfolio_total_cad)
        total_in_cad = convert("USD", "CAD", portfolio_total_usd) + portfolio_total_cad
        portfolio_total = [[format(portfolio_total_usd, '.2f'),
                            format(portfolio_total_cad, '.2f'),
                            format(total_in_usd, '.2f'),
                            format(total_in_cad, '.2f')]]
        portfolio_table = tabulate(portfolio,
                                   headers=["Symbol", "Amount", "Average", "Total", "P/L", "P/L %", "Currency"],
                                   disable_numparse=True)
        portfolio_total_table = tabulate(portfolio_total,
                                         headers=["Total USD", "Total CAD", "Total in USD", "Total in CAD"],
                                         disable_numparse=True)
        return portfolio_table, portfolio_total_table
    except Exception as e:
        print(e)
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
