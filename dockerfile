ARG PYTHON_VERSION=3.9

FROM python:${PYTHON_VERSION}-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=true

RUN \
    export DEBIAN_FRONTEND=noninteractive && \
    apt update && \
    apt install --yes --no-install-recommends libpq-dev gcc && \
    apt clean && rm -rf /var/lib/apt/lists/*

# create virtual environment
ENV VIRTUAL_ENV=/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN useradd --create-home appuser
WORKDIR /home/appuser

COPY requirements.txt .

RUN \
    python -m pip install --no-cache pip -U && \
    python -m pip install --no-cache -r requirements.txt

USER appuser
COPY --chown=appuser:appuser . .

RUN python manage.py collectstatic --noinput

EXPOSE 8080
CMD ["docker/start.sh"]
