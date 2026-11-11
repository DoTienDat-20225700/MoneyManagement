from django.core.exceptions import ImproperlyConfigured


def parse_bool(value, setting_name='DEBUG'):
    """Parse explicit environment booleans and reject ambiguous configuration."""
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in ('true', '1', 'yes'):
        return True
    if normalized in ('false', '0', 'no'):
        return False
    raise ImproperlyConfigured(
        f'{setting_name}={value!r} không hợp lệ; chấp nhận true/false/1/0/yes/no.'
    )
