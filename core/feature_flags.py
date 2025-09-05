from django.conf import settings


def is_enabled(flag_name: str) -> bool:
    """Return True if the given feature flag is enabled.

    Reads from settings.FEATURE_FLAGS with a safe default of False.
    """
    try:
        return bool(getattr(settings, 'FEATURE_FLAGS', {}).get(flag_name, False))
    except Exception:
        return False

