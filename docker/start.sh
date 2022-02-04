#!/bin/bash

python manage.py migrate --noinput

gunicorn mysite.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080
