import src.database as db
from tabulate import tabulate


def sell_position(session, user_id: int, symbol: str, amount: int, price: float, is_usd: bool):
    pass


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
        new_total_price = ex_total + price * amount
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
    user = get_user_or_create(session=session, user_id=user_id, username=username)
    user_id = user[0].id
    positions = session.query(db.Positions).filter_by(user_id=user_id).all()
    portfolio = []
    for pos in positions:
        symbol_id = pos.symbol_id
        symbol = session.query(db.Symbols).filter_by(symbol_id=symbol_id).one().symbol
        total_price = pos.total_price
        amount = pos.amount
        average_price = pos.average_price
        portfolio.append([symbol, total_price, amount, average_price])
    return generate_portfolio_table(portfolio)


def get_symbol_or_create(session, symbol: str):
    symbol_default = {"symbol": symbol}
    return db.get_or_create(session=session, model=db.Symbols, defaults=symbol_default, symbol=symbol)


def get_user_or_create(session, user_id: str, username: str):
    user_default = {"user_id": f"{user_id}", "username": username}
    return db.get_or_create(session=session, model=db.Users, defaults=user_default, user_id=user_id, username=username)


def get_existing_position(session, user_id, symbol_id: int):
    existing = session.query(db.Positions).filter_by(user_id=user_id, symbol_id=symbol_id).first()
    return existing


def generate_portfolio_table(list):
    return tabulate(list, headers=["Symbol", "Total", "Amount", "Average"])
