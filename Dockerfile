# Raspberry Pi Zero W (ARMv6)
FROM arm32v6/python:3.9-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/London

# System deps (Pillow, luma.oled, fonts, tzdata)
RUN apk add --no-cache \
      tzdata \
      libjpeg-turbo freetype \
      jpeg-dev zlib-dev freetype-dev \
      linux-headers

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Python code
COPY rtt.py tube_from_london_underground_py3.py board_sources.py remote_config.py ./
COPY oled_device.py oled_runner.py LondonUndergroundPy3.py ./
COPY config.yml ./config.yml

# Fonts dir (mount or bake in)
RUN mkdir -p /app/fonts

CMD ["python", "-u", "oled_runner.py"]