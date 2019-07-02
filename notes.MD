# Deploy in new environment

- Create `.local_settings`

  - SECRET_KEY
  - DEBUG
  - ALLOWED_HOSTS

- `python manage.py migrate`

- Download data

- `python scripts/parse_xlsx_data.py`

- `python manage.py createsuperuser`
