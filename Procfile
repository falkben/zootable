release: python zootable/manage.py migrate --noinput
web: gunicorn --pythonpath zootable mysite.asgi:application -k uvicorn.workers.UvicornWorker --log-file -
