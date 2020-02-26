release: python zootable/manage.py migrate --noinput
web: newrelic-admin run-program gunicorn --pythonpath zootable mysite.wsgi --log-file -