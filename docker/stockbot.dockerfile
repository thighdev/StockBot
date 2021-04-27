FROM python:3.9.1-buster

ENV PYTHONUNBUFFERED=1
ENV LANG=en_US.utf8

RUN mkdir /apps
RUN mkdir /apps/stockbot
COPY . /apps/stockbot
RUN pip install -r /apps/stockbot/requirements.txt
WORKDIR /apps/stockbot
ENTRYPOINT ["python","/apps/stockbot/stockbot.py"]