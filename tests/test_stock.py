from financelite import Stock, DataRequestException
import pytest

stock = Stock("gme")


def test_chart():
    stock_chart = stock.get_chart(interval="1d", range="5d")
    assert stock_chart


def test_chart_wrong_interval_range():
    with pytest.raises(DataRequestException):
        stock.get_chart("ff", "5d")
    with pytest.raises(DataRequestException):
        stock.get_chart("ff", "ff")


def test_get_live():
    assert stock.get_live()
    with pytest.raises(DataRequestException):
        Stock("somethingdumb").get_live()


def test_stock_str():
    assert str(stock) == "gme"
