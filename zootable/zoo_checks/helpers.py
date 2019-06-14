from django.utils import timezone


def today_time():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
