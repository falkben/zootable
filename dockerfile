ARG PYTHON_VERSION=3.9

FROM python:${PYTHON_VERSION}-slim as build

RUN \
    export DEBIAN_FRONTEND=noninteractive && \
    apt update && \
    apt install --yes --no-install-recommends libpq-dev gcc && \
    apt clean && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /home/appuser

COPY requirements.txt .

RUN \
    python -m pip install --no-cache pip -U && \
    python -m pip install --no-cache -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

ENTRYPOINT []
CMD ["/bin/bash"]

########################################################################################

FROM python:${PYTHON_VERSION}-slim AS runtime

RUN \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && apt-get upgrade --yes && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser
WORKDIR /home/appuser
USER appuser

COPY --from=build --chown=appuser:appuser /venv /venv

ENV PATH=/venv/bin:$PATH VIRTUAL_ENV=/venv

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=true

COPY --from=build --chown=appuser:appuser /home/appuser/ /home/appuser

EXPOSE 8080
CMD ["docker/start.sh"]
