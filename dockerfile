FROM python:3.9-slim-bullseye

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN \
    apt update && \
    apt install -y libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN \
    python -m pip install --no-cache pip -U && \
    python -m pip install --no-cache -r requirements.txt

COPY . /app

EXPOSE 8080
CMD ["gunicorn", "mysite.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080"]
