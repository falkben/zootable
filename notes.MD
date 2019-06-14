# Deploy in new environment

- Create `.local_settings`

  - SECRET_KEY
  - DEBUG
  - ALLOWED_HOSTS

- `python manage.py migrate`

- Download data

- `python scripts/parse_tracks.py`

- `python manage.py createsuperuser`
