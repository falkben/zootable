# Zootable

![Build Status](https://github.com/falkben/zootable/workflows/Python%20application/badge.svg)
[![codecov](https://codecov.io/gh/falkben/zootable/branch/master/graph/badge.svg)](https://codecov.io/gh/falkben/zootable)

Web app to tally zoo animals. See [zootable.com](https://zootable.com) for information.

## License

This project is licensed under the [AGPLv3](http://www.gnu.org/licenses/agpl-3.0.html) license

## Demo

A working demo can be found [here](https://demo.zootable.com)

- username: `demo-user`
- password: `demo-password`

## Install

### Database

#### Install postgres

- `sudo apt install postgresql postgresql-contrib libpq-dev python3.8 python3.8-dev`

#### Config postgres

- Start the database server
  - `sudo service postgresql start`
- Login as `postgres` user
  - `sudo -i -u postgres`
- Create database
  - `createdb zootable`
- Create postgres `zootable` user
  - `createuser --interactive`
  - If don't make superuser, grant permissions to zootable
    - `psql=# grant all privileges on database zootable to zootable;`
- Edit `/etc/postgresql/pg_hba.conf` and insert near the top

  ```
  local   all             zootable                                trust
  ```

- Restart database: `sudo service postgresql restart`

### Setup

- Activate virtual environment
  - `python -m venv venv`
  - `. venv/bin/activate`
- Install
  - `pip install -r requirements.txt`
  - `npm install`
- Create `local_settings.py` with [required variables](mysite/settings.py)
  - `mysite/local_settings.py`
  - `python manage.py migrate`
- `python manage.py createsuperuser`
- Upload data
- From ./: `python zootable/scripts/ingest_xlsx_data.py DATA.xlsx`

## Run

```python
python manage.py runserver
```

or (w/ `browser-sync`)

```cmd
npm start
```

## Deployment check

https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

`python manage.py check --deploy`

## Test

1. Install app in editable mode:

   `pip install -e .`

1. Run from root directory. Pytest settings in [pytest.ini](pytest.ini).

   `pytest`

1. For coverage, coverage settings are in `.coveragerc` and run:

   `pytest --cov=zoo_checks --cov-report=xml`

## Heroku and database actions

### Setup CLI

1. [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli#standalone-installation)
1. `heroku login`

### Database download

1. `heroku pg:backups:capture -a zootable`
1. `heroku pg:backups:download -a zootable`

### Local restore database from dump

1. Possibly drop database before restore:

   1. `sudo -u postgres psql`
   1. `DROP DATABASE zootable;`
   1. `CREATE DATABASE zootable;`

1. Command linked in heroku docs had `-h localhost` but that always required password

   `pg_restore --verbose --clean --no-acl --no-owner -U zootable -d zootable latest.dump`

[heroku docs](https://devcenter.heroku.com/articles/heroku-postgres-import-export)

[postgres docs](https://www.postgresql.org/docs/9.1/app-pgrestore.html)

### To clear sessions

1. First log into heroku bash: `heroku run bash -a zootable`
1. Next clear the sessions: `django-admin clearsessions --settings=mysite.settings`

Documentation on clearing session store: https://docs.djangoproject.com/en/dev/topics/http/sessions/#clearing-the-session-store

### Automatic database backups

`heroku pg:backups:schedule DATABASE_URL --at '02:00 America/Los_Angeles' --app zootable`

See: https://devcenter.heroku.com/articles/heroku-postgres-backups#scheduling-backups

## Update all requirements

[Pur](https://pypi.org/project/pur/)

1. `pip install pur`
1. `pur -r requirements.txt`
1. `pip install -r requirements.txt`
