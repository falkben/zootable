#!/bin/bash

set -euo pipefail

python manage.py migrate --noinput

exec gunicorn \
    --worker-tmp-dir /dev/shm \
    --log-file=- \
    --workers=2 --threads=4 \
    mysite.asgi:application \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8080
