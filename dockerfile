ARG PYTHON_VERSION=3.9

FROM python:${PYTHON_VERSION}-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN \
    apt update && \
    apt install -y libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# create virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

COPY requirements.txt .

RUN \
    python -m pip install --no-cache pip -U && \
    python -m pip install --no-cache -r requirements.txt

COPY . /app

RUN python manage.py collectstatic --noinput

EXPOSE 8080
CMD ["docker/start.sh"]
