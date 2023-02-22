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

### Docker

#### Build

`docker build --pull --tag zootable .`

#### Docker-compose

Create a `.env` file for configured environment variables

`docker-compose up -d`

To store the volume in a different default location (e.g. not on SD card when running on rpi), change the compose file:

```yml
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/ssd/data
```

If this is the first time starting the server, init the superuser:

`docker-compose exec web python manage.py createsuperuser`

If you have a local database you'd rather use instead of the docker-compose volume, you can use the following:

```sh
docker run --rm -p 8080:8080 \
  -v $(pwd)/.env:/home/appuser/.env \
  zootable
```

Debugging:

```sh
docker run --rm -it -p 8080:8080 \
  -v $(pwd)/.env:/home/appuser/.env \
  zootable /bin/bash
```

### Local install

#### Database

##### Install postgres

- `sudo apt install postgresql postgresql-contrib libpq-dev python3.11 python3.11-dev`

##### Config postgres

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
- Edit `/etc/postgresql/14/main/pg_hba.conf` and insert near the top

  ```cfg
  local   all             zootable                                trust
  ```

- Restart database: `sudo service postgresql restart`

#### App Setup

- Create & activate virtual environment
  - `python -m venv venv`
  - `. venv/bin/activate` (or activate.fish)
- Install
  - `pip install -e .[test]` (this installs pytest)
  - `npm install` (installs "hot reloading" `browser-sync`)
- Create `.env` with [required variables](mysite/settings.py)
- Migrate database forward
  - `python manage.py migrate`
- `python manage.py createsuperuser`
- Upload data
  - `python scripts/ingest_xlsx_data.py <DATA.xlsx>`
  - Or upload xlsx file from within the app once running
  - Or ingest from a dumped database (see [below](#heroku-and-database-actions) on pulling and loading a database dump from heroku)

## Run

Standard

```sh
python manage.py runserver
```

or w/ `browser-sync`

```sh
npm start
```

## Deployment check

<https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/>

`python manage.py check --deploy`

## Test

1. Run from root directory. Pytest settings in [pytest.ini](pytest.ini).

   `pytest`

1. For coverage, coverage settings are in `.coveragerc` and run:

   `pytest --cov=zoo_checks --cov-report=xml`

## Heroku and database actions

Note: deploys are being moved to fly.io. See [deploy notes](deploy_notes.md) for more information.

### Setup CLI

1. [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli#standalone-installation)
1. `heroku login`

### Database download

1. `heroku pg:backups:capture -a zootable`
1. `heroku pg:backups:download -a zootable`

### Local restore database from dump

1. Possibly drop local database before restore:

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

Documentation on clearing session store: <https://docs.djangoproject.com/en/dev/topics/http/sessions/#clearing-the-session-store>

### Automatic database backups

`heroku pg:backups:schedule DATABASE_URL --at '02:00 America/New_York' --app zootable`

See: <https://devcenter.heroku.com/articles/heroku-postgres-backups#scheduling-backups>

## Dependencies

### Python dependencies

#### Create a lock file (pip-tools)

Install `pip-tools` into your local environment (`pip install pip-tools`)

To generate compiled dependencies (`requirements.txt` and `requirements-dev.txt`):

1. `pip-compile --generate-hashes --allow-unsafe`
2. `pip-compile --generate-hashes --allow-unsafe requirements-dev.in`

*note:* `--allow-unsafe` option allows pinning `setuptools`. Possibly no longer needed.

#### Upgrade dependencies

1. `pip-compile --upgrade --generate-hashes --allow-unsafe`
2. `pip-compile --upgrade --generate-hashes --allow-unsafe requirements-dev.in`

This updates the lock files while still maintaining constraints in `requirements.in` (or `requirements-dev.in`)

To upgrade to a new **django** version, edit the `requirements.in` file and then run the upgrade compile command above.

#### Install into local environment

```command
pip install -r requirements.txt
pip install -e .
```

For dev

```command
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

### npm

1. `npm install`
2. `npm audit fix`
