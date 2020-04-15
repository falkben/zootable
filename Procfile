release: python zootable/manage.py migrate --noinput
web: newrelic-admin run-program gunicorn --pythonpath zootable mysite.asgi:application -k uvicorn.workers.UvicornWorker --log-file -