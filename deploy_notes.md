# Fly.io deployment notes

Connect to db using [wiregaurd VPN](https://fly.io/docs/reference/private-networking/#private-network-vpn)

Create the config with the flyctl app

In WSL, wireguard isn't easy to use.

Use Windows client instead.

## Show apps

`dig -t txt _apps.internal +short`s

## Connect to db

```cmd
psql postgres://postgres:secret123@appname.internal:**5432**
```

## Deploy

`fly deploy`
