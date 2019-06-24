from django.utils import timezone


def today_time():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


def prior_days(prior_days=3):
    p_days = []
    for p in range(prior_days):
        day = today_time() - timezone.timedelta(days=p + 1)
        p_days.append({"year": day.year, "month": day.month, "day": day.day})

    return p_days
