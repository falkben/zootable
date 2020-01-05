import datetime

from django import template

register = template.Library()


@register.filter
def index(List, i):
    return List[int(i)]


@register.filter(name="range")
def _range(_min, args=None):
    _max, _step = None, None
    if args:
        if not isinstance(args, int):
            _max, _step = map(int, args.split(","))
        else:
            _max = args
    args = filter(None, (_min, _max, _step))
    return range(*args)


@register.filter()
def addDays(days, start_date=None):
    if start_date is None:
        start_date = datetime.date.today()

    newDate = start_date + datetime.timedelta(days=days)
    return newDate
