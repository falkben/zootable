# Zootable

[![Build Status](https://travis-ci.org/falkben/zootable.svg?branch=master)](https://travis-ci.org/falkben/zootable)

Web app to tally zoo animals. See [zootable.com](https://zootable.com) for information.

## License

This project is licensed under the [AGPLv3](http://www.gnu.org/licenses/agpl-3.0.html) license

## Run

- Install `pip install -r requirements.txt`

- Create `zootable/mysite/local_settings.py`

  - SECRET_KEY
  - DEBUG
  - ALLOWED_HOSTS

- From zootable/: `python manage.py migrate`

- `python manage.py createsuperuser`

- Download data

- From ./: `python scripts/ingest_xlsx_data.py DATA.xlsx`

## Deployment check

- https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

  `python manage.py check --deploy`

## Test

`pytest zootable`
