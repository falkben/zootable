from .settings import *

# Override STATICFILES_STORAGE setting
# Avoid "ValueError: Missing staticfiles manifest entry" during testing
# see: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#django.contrib.staticfiles.storage.ManifestStaticFilesStorage.manifest_strict
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
