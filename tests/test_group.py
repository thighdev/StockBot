from financelite import (
    Group,
    Stock,
    ItemNotValidException,
    TickerNotInGroupException,
    DataRequestException,
)
import pytest

gme = Stock("gme")
bb = Stock("bb")
dumb = Stock("fewafsdfaewaf")


def test_group():
    group = Group()
    assert group
    group = Group([gme, bb])
    assert group


def test_group_add_remove_ticker():
    group = Group([gme])
    assert len(group.tickers) == 1
    group.add_ticker("bb")
    assert len(group.tickers) == 2
    group.remove_ticker("gme")
    assert len(group.tickers) == 1
    with pytest.raises(TickerNotInGroupException):
        group.remove_ticker("ff")


def test_group_quotes():
    group = Group([gme, bb])
    assert len(group.get_quotes()) == 2


def test_group_quotes_invalid_ticker():
    with pytest.raises(DataRequestException):
        group = Group([gme, dumb])
        group.get_quotes()


def test_group_quotes_cherry_pick():
    group = Group()
    group.add_ticker("gme")
    data = group.get_quotes(cherrypicks=["shortName"])
    assert len(data.pop().keys()) == 1
    data = group.get_quotes(cherrypicks=["shortName", "longName"])
    assert len(data.pop().keys()) == 2
    data = group.get_quotes(cherrypicks=["shortName", "longName"], exclude=True)
    assert len(data.pop().keys()) != 2


def test_group_quotes_cherry_pick_invalid():
    group = Group()
    group.add_ticker("gme")
    with pytest.raises(ItemNotValidException):
        group.get_quotes(cherrypicks=["somethingDumb"])
    with pytest.raises(ItemNotValidException):
        group.get_quotes(cherrypicks=["somethingDumb"], exclude=True)
