release: python manage.py migrate --noinput
web: gunicorn mysite.asgi:application -k uvicorn.workers.UvicornWorker --log-file -
