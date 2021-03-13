from financelite import News, NoNewsFoundException
import pytest


def test_news():
    news = News().get_news("gme")
    assert len(news) == 10


def test_news_count():
    news = News().get_news("gme", count=5)
    assert len(news) == 5
    news = News().get_news("gme", count=15)
    assert len(news) == 15


def test_news_invalid_ticker():
    with pytest.raises(NoNewsFoundException):
        News().get_news("absolutely_wrong", count=5)
