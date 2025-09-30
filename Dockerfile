# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/London

RUN apt-get update && apt-get install -y --no-install-recommends \
      tzdata ca-certificates \
      libjpeg62-turbo-dev zlib1g-dev libfreetype6-dev \
      alsa-utils mpg123 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rtt.py tube_from_london_underground_py3.py board_sources.py remote_config.py ./
COPY oled_device.py oled_runner.py LondonUndergroundPy3.py ./
COPY config.yml ./config.yml

RUN mkdir -p /app/fonts /app/cache/audio

CMD ["python", "-u", "oled_runner.py"]
