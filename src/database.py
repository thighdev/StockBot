from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, Integer, create_engine, Text, DateTime, Float, Boolean, BigInteger)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import ClauseElement

Base = declarative_base()
Session = sessionmaker()


class Users(Base):
    __tablename__ = "users"

    id = Column(BigInteger(), primary_key=True)
    user_id = Column(Text())
    username = Column(Text())


class Symbols(Base):
    __tablename__ = "symbols"

    symbol_id = Column(Integer(), primary_key=True)
    symbol = Column(Text())


class Positions(Base):
    __tablename__ = "positions"

    position_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer())
    symbol_id = Column(Integer())
    total_price = Column(Float())
    average_price = Column(Float())
    amount = Column(Integer())
    is_usd = Column(Boolean())


def connect(url):
    """
    creates the engine and session
    :param url: sqlalchemy url
    """
    engine = create_engine(url)
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)


def get_or_create(session, model, defaults=None, **kwargs):
    """
    gets an existing reocrd or creates a new one based on kwargs
    :param session: existing session
    :param model: sqlalchemy model
    :param defaults: if model needs to be created, values to use
    :param kwargs: pass selection key/value pairs
    :return: model instance, boolean True if created new record
    """
    """
    gets an existing record or creates a new one based on kwargs

    """
    instance = session.query(model).filter_by(**kwargs).one_or_none()
    if instance:
        return instance, False
    else:
        params = {k: v for k, v in kwargs.items() if not isinstance(v, ClauseElement)}
        params.update(defaults or {})
        instance = model(**params)
        try:
            session.add(instance)
            session.commit()
        except Exception as e:
            # The actual exception depends on the specific database so we catch all exceptions.
            # This is similar to the official documentation:
            # https://docs.sqlalchemy.org/en/latest/orm/session_transaction.html
            print(f"exception: {e}")
            session.rollback()
            instance = session.query(model).filter_by(**kwargs).one()
            return instance, False
        else:
            return instance, True
