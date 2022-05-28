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

## printenv

`flyctl ssh console`

`printenv`

## backup db

Proxy postgres server to `localhost`:

```sh
flyctl proxy 15432:5432 -a zootable-na-db
```

Dump the database to `latest.dump`:

note: need to have same version as server version (14.2)

```sh
export PGPASSWORD=[PASSWORD]
pg_dump -Fc --no-acl --no-owner -h localhost -p 15432 -v -U na_zootable zootable > latest.dump
```

(command above mimics heroku's)

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

## Certs

This is a one-time setup (example for `test-na.zootable.com`)

Add CNAME or A record to cloudflare for the subdomain.

```sh
flyctl certs create test-na.zootable.com
```

Then check on it with

```sh
flyctl certs check test-na.zootable.com
```
