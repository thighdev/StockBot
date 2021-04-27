import src.database as db
import discord
from financelite import Stock, Group
from src.database import Session
from discord.ext import commands
from tabulate import tabulate
from forex_python.converter import CurrencyRates
from typing import List, Union


class NotEnoughPositionsToSell(Exception):
    pass


class NoPositionsException(commands.CommandError):
    pass


class NotAmerican(Exception):
    pass


class WalletHasNoBookValues(BaseException):
    pass


def buy_position(user_id: str, username: str, symbol: str, amount: int, price: float):
    session = Session()
    bought_price, currency = Stock(ticker=symbol).get_live()
    if currency not in ["USD", "CAD"]:
        raise NotAmerican
    bought_price = price if price else bought_price
    try:
        symbol = get_symbol_or_create(session, symbol)
        symbol_id = symbol[0].symbol_id
        user = get_user_or_create(session, user_id=user_id, username=username)
        user_id = user[0].id
        ex_total, ex_amount = 0, 0
        existing = get_existing_position(
            session=session, user_id=user_id, symbol_id=symbol_id
        )
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
            position_row = db.Positions(
                user_id=user_id,
                symbol_id=symbol_id,
                total_price=new_total_price,
                average_price=new_average_price,
                amount=new_amount,
            )
            session.add(position_row)
        return bought_price, currency
    finally:
        session.commit()
        session.close()


def sell_position(user_id: str, username: str, symbol: str, amount: int, price: float):
    # TODO: maybe add cash attr for users
    session = Session()
    sold_price, currency = Stock(symbol).get_live()
    if currency not in ["USD", "CAD"]:
        raise NotAmerican
    sold_price = price if price else sold_price
    try:
        symbol = get_symbol_or_create(session, symbol)
        symbol_id = symbol[0].symbol_id
        user = get_user_or_create(session, user_id=user_id, username=username)
        user_id = user[0].id
        existing = get_existing_position(
            session=session, user_id=user_id, symbol_id=symbol_id
        )
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


def calculate_pl(live: float, book_value: float) -> tuple:
    pl = live - book_value
    pl_percent = (pl / book_value) * 100
    return pl, pl_percent


def summary_handler(summary: dict, format_type: Union[discord.Embed, List]):
    for key, value in summary.items():
        book_value = two_decimal(value.get("book_value"))
        live = two_decimal(value.get("live"))
        pl = value.get("pl")
        pl_percent = value.get("pl_percent")
        if pl > 0:
            prefix = "+"
        elif pl < 0:
            prefix = "-"
        else:
            prefix = ""
        pl_string = (
            f"{prefix + two_decimal(abs(pl))}({prefix + two_decimal(abs(pl_percent))}%)"
        )

        if isinstance(format_type, discord.Embed):
            format_type.add_field(
                name=f"Summary {key}",
                value=f"> Book Value: {book_value}\n"
                f"> Current Total: {live}\n"
                f"> P/L(%): {pl_string}",
            )
        else:
            format_type.append([prefix + key, book_value, live, pl_string])


class CurrencyWallet:
    def __init__(self):
        self.usd_book_value = 0.0
        self.usd_live = 0.0
        self.cad_book_value = 0.0
        self.cad_live = 0.0

    def add_currency(self, currency: str, book_value: float, live: float):
        if currency == "USD":
            self.usd_book_value += book_value
            self.usd_live += live
        else:
            self.cad_book_value += book_value
            self.cad_live += live

    @staticmethod
    def _forex(init: str, final: str, value: float):
        return CurrencyRates().convert(base_cur=init, dest_cur=final, amount=value)

    def summary(self) -> dict:
        book_value_in_usd = self.usd_book_value + self._forex(
            "CAD", "USD", self.cad_book_value
        )
        book_value_in_cad = self.cad_book_value + self._forex(
            "USD", "CAD", self.usd_book_value
        )
        live_in_usd = self.usd_live + self._forex("CAD", "USD", self.cad_live)
        live_in_cad = self.cad_live + self._forex("USD", "CAD", self.usd_live)
        pl_in_usd, pl_in_usd_percent = calculate_pl(live_in_usd, book_value_in_usd)
        pl_in_cad, pl_in_cad_percent = calculate_pl(live_in_cad, book_value_in_cad)
        summary = {}
        if self.usd_book_value:
            pl_usd, pl_usd_percent = calculate_pl(self.usd_live, self.usd_book_value)
            summary["USD"] = {
                "book_value": self.usd_book_value,
                "live": self.usd_live,
                "pl": pl_usd,
                "pl_percent": pl_usd_percent,
            }
        if self.cad_book_value:
            pl_cad, pl_cad_percent = calculate_pl(self.cad_live, self.cad_book_value)
            summary["CAD"] = {
                "book_value": self.cad_book_value,
                "live": self.cad_live,
                "pl": pl_cad,
                "pl_percent": pl_cad_percent,
            }
        if not self.usd_book_value and not self.cad_book_value:
            raise WalletHasNoBookValues

        summary_in_currency_total = {
            "Total in USD": {
                "book_value": book_value_in_usd,
                "live": live_in_usd,
                "pl": pl_in_usd,
                "pl_percent": pl_in_usd_percent,
            },
            "Total in CAD": {
                "book_value": book_value_in_cad,
                "live": live_in_cad,
                "pl": pl_in_cad,
                "pl_percent": pl_in_cad_percent,
            },
        }
        summary = summary | summary_in_currency_total
        return summary


def handle_positions(
    pos_group: Group,
    pos_dict: dict,
    currency_wallet: CurrencyWallet,
    format_type: Union[discord.Embed, List],
):
    live_info = pos_group.get_quotes(
        cherrypicks=["symbol", "regularMarketPrice", "currency"]
    )

    for info in live_info:
        symbol = info.get("symbol")
        live = info.get("regularMarketPrice")
        amount = pos_dict.get(symbol).get("amount")
        book_value = pos_dict.get(symbol).get("book_value")
        average = pos_dict.get(symbol).get("average")
        currency = info.get("currency")
        live_total = live * amount
        pl, pl_percent = calculate_pl(live=live_total, book_value=book_value)
        pl = two_decimal(pl)
        pl_percent = two_decimal(pl_percent)
        currency_wallet.add_currency(
            currency=currency, book_value=book_value, live=live_total
        )
        if live > average:
            symbol = "+" + symbol
            pl = "+" + pl
            pl_percent = f"+{pl_percent}"
        elif average > live:
            symbol = "-" + symbol
        else:
            pass
        if isinstance(format_type, discord.Embed):
            format_type.add_field(
                name=f"**{symbol}**",
                value=f"> Amount: x {amount}\n"
                f"> Average Price: {two_decimal(average)}\n"
                f"> Live Price: {two_decimal(live)}\n"
                f"> Book Value: {two_decimal(book_value)}\n"
                f"> Current Total: {two_decimal(live_total)}\n"
                f"> P/L (%): {pl} ({pl_percent}%)\n"
                f"> Currency: {currency}",
            )
        else:
            format_type.append(
                [
                    symbol,
                    f"x {amount}",
                    two_decimal(average),
                    two_decimal(live),
                    two_decimal(book_value),
                    two_decimal(live_total),
                    f"{pl} ({pl_percent}%)",
                    currency,
                ]
            )


def get_portfolio(user_id: str, username: str, mobile: bool):
    session = Session()
    try:
        user = get_user_or_create(session=session, user_id=user_id, username=username)
        user_id = user[0].id
        positions = session.query(db.Positions).filter_by(user_id=user_id).all()
        if not positions:
            raise NoPositionsException
        pf_list = (
            list()
            if not mobile
            else discord.Embed(
                title=f"{username}'s Portfolio", colour=discord.Colour.green()
            )
        )
        currency_wallet = CurrencyWallet()
        pos_group = Group()
        pos_dict = dict()

        for item in positions:
            symbol = (
                session.query(db.Symbols)
                .filter_by(symbol_id=item.symbol_id)
                .one()
                .symbol
            )
            pos_group.add_ticker(symbol)
            pos_dict[symbol] = dict(
                book_value=item.total_price,
                average=item.average_price,
                amount=item.amount,
            )

        handle_positions(
            pos_group=pos_group,
            pos_dict=pos_dict,
            currency_wallet=currency_wallet,
            format_type=pf_list,
        )
        if mobile:
            portfolio_table = pf_list
        else:
            headers = [
                "Symbol",
                "Amount",
                "Average Price",
                "Live Price",
                "Book Value",
                "Current Total",
                "P/L (%)",
                "Currency",
            ]
            pf_len = len(pf_list)
            if pf_len > 10:
                chunking = pf_len // 10
                if pf_len % 10:
                    chunking += 1
            else:
                chunking = 1
            portfolio_table = []
            for _ in range(chunking):
                chunk = pf_list[:10]
                portfolio_table.append(
                    tabulate(
                        chunk,
                        headers=headers,
                        disable_numparse=True,
                    )
                )
                del pf_list[:10]

        wallet_summary = currency_wallet.summary()
        if mobile:
            summary = discord.Embed(
                title=f"{username}'s Portfolio Summary", colour=discord.Colour.green()
            )
            summary_handler(wallet_summary, summary)
        else:
            summary = []
            summary_handler(wallet_summary, summary)
            summary = tabulate(
                summary,
                headers=["Currency", "Book Value", "Current Total", "P/L(%)"],
                stralign="left",
                disable_numparse=True,
            )
        return portfolio_table, summary
    finally:
        session.close()


def get_symbol_or_create(session, symbol: str):
    symbol_default = {"symbol": symbol.upper()}
    return db.get_or_create(
        session=session, model=db.Symbols, defaults=symbol_default, symbol=symbol
    )


def get_user_or_create(session, user_id: str, username: str):
    user_default = {"user_id": f"{user_id}", "username": username}
    return db.get_or_create(
        session=session,
        model=db.Users,
        defaults=user_default,
        user_id=user_id,
        username=username,
    )


def get_existing_position(session, user_id, symbol_id: int):
    existing = (
        session.query(db.Positions)
        .filter_by(user_id=user_id, symbol_id=symbol_id)
        .first()
    )
    return existing


def two_decimal(number: float):
    return format(number, ".2f")
