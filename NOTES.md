# Notes

## Check before deployment

- https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/
- `python manage.py check --deploy`

## Deploy in new environment

- Create `local_settings`
- `python manage.py migrate`
- Download database data
- `python scripts/parse_tracks.py`
- `python manage.py createsuperuser`
