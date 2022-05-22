# Fly.io deployment notes

## Show apps

`dig -t txt _apps.internal +short`

## Connect to db

`flyctl postgres connect -a zootable-na-db`

Can also proxy to localhost using `flyctl proxy`.

## Deploy

`flyctl deploy`

## Database connected to app

`flyctl postgres connect` will create a database named the same as the app name. Our database dumps just expect the name "zootable". So make sure to use the correct database, especially when restoring from backup.

## Ingest secrets into fly environment

```sh
cat .private/.env-fly | flyctl secrets import
```

## Upload db dump

Proxy postgres server to `localhost`:

```sh
flyctl proxy 15432:5432 -a zootable-na-db
```

Set the POSTGRES URI:

```sh
FLY_POSTGRES_URI=postgres://na_zootable:[PASSWORD]@localhost:15432/zootable
```

Apply the database dump

```sh
pg_restore --verbose --clean --no-acl --no-owner -U zootable -d "$FLY_POSTGRES_URI" latest.dump
```
