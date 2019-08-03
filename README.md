# Zootable

[![Build Status](https://travis-ci.org/falkben/zootable.svg?branch=master)](https://travis-ci.org/falkben/zootable)

Web app to tally zoo animals

## License

This project is licensed under the [AGPLv3](http://www.gnu.org/licenses/agpl-3.0.html) license

## Deployment notes

- Create `.local_settings`

  - SECRET_KEY
  - DEBUG
  - ALLOWED_HOSTS

- `python manage.py migrate`

- Download data

- `python scripts/ingest_xlsx_data.py DATA.xlsx`

- `python manage.py createsuperuser`

- https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

  `python manage.py check --deploy`

## Test

`pytest zootable`
