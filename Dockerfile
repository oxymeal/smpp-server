FROM python:3.6-alpine

WORKDIR /app

RUN apk --no-cache add \
  zeromq \
  alpine-sdk

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Clean up to free some disk space
RUN apk del \
alpine-sdk

COPY . /app

CMD python3.6 main.py
