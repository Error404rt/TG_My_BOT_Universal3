FROM python:3.12 AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock /app/
RUN pip install poetry
RUN poetry install --no-root --only main

COPY . /app

CMD ["poetry", "run", "python", "main.py"]