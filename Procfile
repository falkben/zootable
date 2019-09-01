release: python manage.py migrate --noinput
web: gunicorn --pythonpath zootable mysite.wsgi --log-file -