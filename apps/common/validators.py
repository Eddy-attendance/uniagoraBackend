"""
Generic validators reused by more than one domain app.
"""

import re

from django.core.exceptions import ValidationError

PHONE_NUMBER_REGEX = re.compile(r"^\+?[0-9]{7,15}$")


def validate_phone_number(value: str) -> None:
    if not PHONE_NUMBER_REGEX.match(value):
        raise ValidationError(
            "Enter a valid phone number (7-15 digits, optional leading '+')."
        )
