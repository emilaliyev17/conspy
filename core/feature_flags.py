from django.conf import settings


def is_enabled(flag_name: str) -> bool:
    from django.conf import settings as _settings
    return getattr(_settings, flag_name, False)
