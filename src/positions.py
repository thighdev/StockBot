import src.database as db
import discord
from financelite import Stock
from src.database import Session
from discord.ext import commands
from src.functions import get_live_price
from tabulate import tabulate
from forex_python.converter import CurrencyRates
from typing import List


class NotEnoughPositionsToSell(Exception):
    pass


class NoPositionsException(commands.CommandError):
    pass


def sell_position(user_id: str, username: str, symbol: str, amount: int, price: float):
    # TODO: maybe add cash attr for users
    session = Session()
    sold_price, currency = Stock(symbol).get_live()
    sold_price = price if price else sold_price
    try:
        symbol = get_symbol_or_create(session, symbol, currency)
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


class PortfolioCalculator:
    def __init__(self, main_currency: str):
        self.main_currency = main_currency
        self.live_total = float()
        self.average_total = float()
        self.live_currencies_total = dict()
        self.average_currencies_total = dict()

    @staticmethod
    def _forex(init: str, final: str, value: float):
        return CurrencyRates().convert(base_cur=init, dest_cur=final, amount=value)

    @staticmethod
    def _accumulate_or_create(data: dict, key: str, value: float, amount: int):
        if data.get(key):
            data[key] += value * amount
        else:
            data[key] = value * amount

    def add_data(self, currency: str, live: float, average: float, amount: int):
        self.live_total += self._to_currency(currency=currency, value=live) * amount
        self.average_total += (
            self._to_currency(currency=currency, value=average) * amount
        )
        self._accumulate_or_create(
            data=self.live_currencies_total, key=currency, value=live, amount=amount
        )
        self._accumulate_or_create(
            data=self.average_currencies_total,
            key=currency,
            value=average,
            amount=amount,
        )

    def convert_all(self, data: dict, currency: str) -> float:
        total = float()
        for key, value in data.items():
            if key != currency:
                total += self._forex(init=key, final=currency, value=value)
                continue
            total += value
        return total

    def _to_currency(self, currency: str, value: float) -> float:
        return self._forex(init=currency, final=self.main_currency, value=value)

    def get_total_in_currencies(self, data: dict) -> dict:
        converted = dict()
        for key, value in data.items():
            converted[key] = self.convert_all(data=data, currency=key)
        return converted

    @property
    def total_live_in_currencies(self) -> dict:
        return self.get_total_in_currencies(data=self.live_currencies_total)

    @property
    def total_average_in_currencies(self) -> dict:
        return self.get_total_in_currencies(data=self.average_currencies_total)

    @staticmethod
    def calculate_pl(live: float, average: float) -> tuple:
        pl = live - average
        pl_percent = (pl / average) * 100
        return pl, pl_percent

    @property
    def total_pl(self) -> tuple:
        return self.calculate_pl(live=self.live_total, average=self.average_total)

    @property
    def total_pl_currencies(self) -> dict:
        pl = dict()
        for key, value in self.total_live_in_currencies.items():
            live = value
            average = self.total_average_in_currencies.get(key)
            pl[key] = self.calculate_pl(live=live, average=average)
        return pl


def get_portfolio(user_id: str, username: str, mobile: bool, main: str):
    session = Session()
    try:
        user = get_user_or_create(session=session, user_id=user_id, username=username)
        user_id = user[0].id
        positions = session.query(db.Positions).filter_by(user_id=user_id).all()
        if not positions:
            raise NoPositionsException
        portfolio = PortfolioCalculator(main)
        pf_list = (
            list() if not mobile else discord.Embed(title=f"{username}'s Portfolio")
        )
        for item in positions:
            symbol = session.query(db.Symbols).filter_by(symbol_id=item.symbol_id).one()
            currency = symbol.currency
            live = Stock(symbol.symbol).get_live()[0]
            average = item.average_price
            amount = item.amount
            pl, pl_percent = PortfolioCalculator.calculate_pl(
                live=live * amount, average=average * amount
            )
            pl = two_decimal(pl)
            pl_percent = two_decimal(pl_percent)
            portfolio.add_data(
                currency=currency, live=live, average=average, amount=amount
            )
            symbol = symbol.symbol
            if live > average:
                symbol = "+" + symbol
                pl = "+" + pl
                pl_percent = f"+{pl_percent}"
            elif average > live:
                symbol = "-" + symbol
            else:
                pass
            if mobile:
                pf_list.add_field(
                    name=f"**{symbol}**",
                    value=f"> Amount: x {amount}\n"
                    f"> Average Price: {two_decimal(average)}\n"
                    f"> Live Price: {two_decimal(live)}\n"
                    f"> Total: {two_decimal(live * amount)}\n"
                    f"> P/L (%): {pl} ({pl_percent}%)\n"
                    f"> Currency: {currency}",
                )
            else:
                pf_list.append(
                    [
                        symbol,
                        f"x {amount}",
                        two_decimal(average),
                        two_decimal(live),
                        two_decimal(live * amount),
                        f"{pl} ({pl_percent}%)",
                        currency,
                    ]
                )
        portfolio_table = (
            tabulate(
                pf_list,
                headers=[
                    "Symbol",
                    "Amount",
                    "Average Price",
                    "Live Price",
                    "Total Value",
                    "P/L (%)",
                    "Currency",
                ],
                disable_numparse=True,
            )
            if not mobile
            else pf_list
        )

        total = portfolio.live_total
        total_pl, total_pl_percent = portfolio.total_pl
        if not mobile:
            currencies_summary = []
            for key, value in portfolio.total_live_in_currencies.items():
                pl, pl_percent = portfolio.total_pl_currencies.get(key)
                currencies_summary.append(
                    [
                        key,
                        two_decimal(value),
                        f"{two_decimal(pl)} ({two_decimal(pl_percent)}%)",
                    ]
                )
            currencies_summary = tabulate(
                currencies_summary,
                headers=["Total in Currency", "Total Value", "P/L (%)"],
                stralign="left",
                numalign="left",
            )
            summary = tabulate(
                [
                    [
                        two_decimal(total),
                        f"{two_decimal(total_pl)} ({two_decimal(total_pl_percent)}%)",
                    ]
                ],
                headers=[f"Total in {main}", f"Total P/L in {main} (%)"],
                stralign="left",
                numalign="left",
            )
        else:
            currencies_summary = discord.Embed(title="Total value in Currencies")
            for key, value in portfolio.total_live_in_currencies.items():
                pl, pl_percent = portfolio.total_pl_currencies.get(key)
                currencies_summary.add_field(
                    name=f"**{key}**",
                    value=f"> Total: {value}\n"
                    f"> P/L (%): {two_decimal(pl)} ({two_decimal(pl_percent)}%)",
                )
            summary = discord.Embed(title=f"Total value in {main}")
            summary.add_field(
                name=f"{main}",
                value=f"> Total: {two_decimal(total)}\n"
                f"> P/L (%): {two_decimal(total_pl)} ({two_decimal(total_pl_percent)}%)",
            )
        return portfolio_table, currencies_summary, summary
    finally:
        session.close()


def get_symbol_or_create(session, symbol: str, currency: str):
    symbol_default = {"symbol": symbol.upper(), "currency": currency}
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


def convert(initial, final, amount):
    return CurrencyRates().convert(base_cur=initial, dest_cur=final, amount=amount)


def neg_zero_handler(neg_zero):
    return "0.00" if neg_zero == "-0.00" else neg_zero


def two_decimal(number: float):
    return format(number, ".2f")


def get_total_usd_cad(usd, cad):
    total_in_usd = usd + convert("CAD", "USD", cad)
    total_in_cad = cad + convert("USD", "CAD", usd)
    return total_in_usd, total_in_cad
