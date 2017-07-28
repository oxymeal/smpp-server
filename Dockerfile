FROM python:3.6-alpine

RUN apk --no-cache add \
  zeromq \
  alpine-sdk

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

# Clean up to free some disk space
RUN apk del \
  alpine-sdk

CMD python3.6 main.py
