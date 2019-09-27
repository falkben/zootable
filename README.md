# Zootable

[![Build Status](https://travis-ci.org/falkben/zootable.svg?branch=master)](https://travis-ci.org/falkben/zootable)

Web app to tally zoo animals. See [zootable.com](https://zootable.com) for information.

## License

This project is licensed under the [AGPLv3](http://www.gnu.org/licenses/agpl-3.0.html) license

## Install

### Database

#### Install postgres

- `sudo apt install postgresql postgresql-contrib libpq-dev python3.7 python3.7-dev`

#### Config postgres

- Start the database server
  - `sudo service postgresql start`
- Login as `postgres` user
  - `sudo -i -u postgres`
- Create database
  - `createdb zootable`
- Create postgres user
  - `zootable` `createuser --interactive`
  - If don't make superuser, grant permissions to zootable
    - `psql=# grant all privileges on database zootable to zootable;`
- Edit `/etc/postgresql/pg_hba.conf` and insert near the top
  ```
  local   all             zootable                                trust
  ```
- Restart database: `sudo service postgresql restart`

### Setup

- Activate virtual environment
- Install
  - `pip install -r requirements.txt`
- Create `local_settings.py` with [required variables](zootable/mysite/settings.py)
  - `zootable/mysite/local_settings.py`
- From `zootable/`:
  - `python manage.py migrate`
- `python manage.py createsuperuser`
- Upload data
- From ./: `python zootable/scripts/ingest_xlsx_data.py DATA.xlsx`

## Run

from `zootable/`

```python
python manage.py runserver
```

## Deployment check

https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

`python manage.py check --deploy`

## Test

Run from root directory.  Specify folder for django application:

`pytest zootable`

In vscode, add command line argument "zootable":

```json
"python.testing.pytestArgs": [
    "zootable"
]
```

## Update all requirements

[Pur](https://pypi.org/project/pur/)

`pip install pur`
`pur -r requirements.txt`
`pip install -r requirements.txt`
