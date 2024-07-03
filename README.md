# Zootable

![Build Status](https://github.com/falkben/zootable/workflows/Python%20application/badge.svg)
[![codecov](https://codecov.io/gh/falkben/zootable/branch/master/graph/badge.svg)](https://codecov.io/gh/falkben/zootable)

Web app to tally zoo animals. See [zootable.com](https://zootable.com) for information.

## License

This project is licensed under the [AGPLv3](http://www.gnu.org/licenses/agpl-3.0.html) license

## Install

### Docker

#### Build

`docker build --pull --tag zootable .`

#### Docker compose

Create a `.env` file for configured environment variables

`docker compose up -d`

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

`docker compose exec web python manage.py createsuperuser`

If you have a local database you'd rather use instead of the docker compose volume, you can use the following:

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
- Create `.env` with [required variables](mysite/settings.py)
- Migrate database forward
  - `python manage.py migrate`
- `python manage.py createsuperuser`
- Upload data
  - `python scripts/ingest_xlsx_data.py <DATA.xlsx>`
  - Or upload xlsx file from within the app once running

## Run

Standard

```sh
python manage.py runserver
```

## Database actions

### Database download

Proxy postgres server (fly.io) to `localhost`:

```sh
flyctl proxy 15432:5432 -a zootable-na-db
```

Dump the database to `latest.dump`:

note: need to have same version as server version (14.2)

```sh
PGPASSWORD=[PASSWORD] pg_dump -Fc --no-acl --no-owner -h localhost -p 15432 -v -U na_zootable zootable > latest.dump
```

### Restore database from dump

1. Drop local database before restore (optional):
   1. `sudo -u postgres psql`
   2. `DROP DATABASE zootable;`
   3. `CREATE DATABASE zootable;`
2. Restore from the dump
   1. `pg_restore --verbose --clean --no-acl -p 5432 --no-owner -U zootable -d zootable latest.dump`

## Deployment check

<https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/>

`python manage.py check --deploy`

## Test

1. Run from root directory. Pytest settings in [pytest.ini](pytest.ini).

   `pytest`

1. For coverage, coverage settings are in `.coveragerc` and run:

   `pytest --cov=zoo_checks --cov-report=xml`

## Dependencies

### Python dependencies

#### Create a lock file (pip-tools)

Install `pip-tools` into your local environment (`pip install pip-tools`)

To generate compiled dependencies (`requirements.txt` and `requirements-dev.txt`):

```sh
uv pip compile -o requirements.txt --generate-hashes requirements.in --quiet && \
uv pip compile -o requirements-dev.txt --generate-hashes requirements-dev.in --quiet
```

*note:* `--allow-unsafe` option allows pinning `setuptools`. Possibly no longer needed.

#### Upgrade dependencies

```sh
uv pip compile -o requirements.txt --generate-hashes requirements.in --upgrade --quiet && \
uv pip compile -o requirements-dev.txt --generate-hashes requirements-dev.in --upgrade --quiet
```

This updates the lock files while still maintaining constraints in `requirements.in` (or `requirements-dev.in`)

To upgrade to a new **django** version, edit the `requirements.in` file and then run the upgrade compile command above.

#### Install into local environment

```sh
pip install -r requirements.txt
pip install -e .
```

For dev

```sh
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```
