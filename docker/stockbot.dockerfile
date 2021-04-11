FROM python:3.9.1-buster

RUN mkdir /apps
RUN mkdir /apps/stockbot
COPY . /apps/stockbot
RUN pip install -r /apps/stockbot/requirements.txt
WORKDIR /apps/stockbot

ENV PYTHONUNBUFFERED=1
ENV LANG=en_US.utf8
