"""
Shared Validation Utilities

Extracts the duplicated validation patterns found across:
  - students/validators.py  (phone, email, date range, status transition, CSV headers, batch size)
  - finance/validators.py   (status transition)
  - attendance/validators.py (status, date range)
  - results/validators.py   (status transition, CSV headers, batch size)
  - admissions/validators.py (reuses StudentValidator for phone/email)

Usage:
    from apps.shared.validators import (
        validate_nigerian_phone,
        validate_email_format,
        validate_status_transition,
        validate_date_range,
        validate_csv_headers,
        validate_batch_size,
    )
"""

import re
from datetime import date, datetime
from typing import Dict, List, Optional, Sequence, Union

from django.core.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Compiled patterns (Nigerian-specific)
# ---------------------------------------------------------------------------
NIGERIAN_PHONE_PATTERN = re.compile(r"^0[789]\d{9}$|^\+234[789]\d{9}$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# ---------------------------------------------------------------------------
# Contact validators
# ---------------------------------------------------------------------------
def validate_nigerian_phone(phone: Optional[str], field_name: str = "phone") -> Optional[bool]:
    """
    Validate a Nigerian phone number (``080…``, ``+234…``).

    Returns ``None`` when *phone* is falsy (field is optional).
    Raises ``ValidationError`` on bad format.
    """
    if not phone:
        return None
    if not NIGERIAN_PHONE_PATTERN.match(phone):
        raise ValidationError(
            {field_name: f"Invalid phone number format: {phone}. "
                         "Expected: 08012345678 or +2348012345678"}
        )
    return True


def validate_email_format(email: Optional[str], field_name: str = "email") -> Optional[bool]:
    """
    Validate a basic email format.

    Returns ``None`` when *email* is falsy.
    Raises ``ValidationError`` on bad format.
    """
    if not email:
        return None
    if not EMAIL_PATTERN.match(email):
        raise ValidationError(
            {field_name: f"Invalid email format: {email}"}
        )
    return True


# ---------------------------------------------------------------------------
# Status transition
# ---------------------------------------------------------------------------
def validate_status_transition(
    current_status: str,
    new_status: str,
    valid_transitions: Dict[str, List[str]],
    error_class: type = ValidationError,
) -> bool:
    """
    Validate a status transition against a mapping of allowed transitions.

    Args:
        current_status:    The object's current status value.
        new_status:        The desired new status value.
        valid_transitions: ``{status: [allowed_targets, …]}`` mapping.
        error_class:       Exception class to raise on failure
                           (default ``django.core.exceptions.ValidationError``).
    """
    if current_status == new_status:
        return True

    allowed = valid_transitions.get(current_status, [])
    if new_status not in allowed:
        raise error_class(
            f"Cannot transition from '{current_status}' to '{new_status}'"
        )
    return True


# ---------------------------------------------------------------------------
# Date range
# ---------------------------------------------------------------------------
def validate_date_range(
    start_date: date,
    end_date: date,
    max_days: int = 365,
) -> bool:
    """
    Validate that *start_date* ≤ *end_date* and the span is within *max_days*.

    Raises ``ValidationError`` on failure.
    """
    if start_date > end_date:
        raise ValidationError("Start date cannot be after end date")
    if (end_date - start_date).days > max_days:
        raise ValidationError(f"Date range cannot exceed {max_days} days")
    return True


# ---------------------------------------------------------------------------
# Bulk-operation helpers
# ---------------------------------------------------------------------------
def validate_csv_headers(
    headers: Sequence[str],
    required_fields: Sequence[str],
) -> bool:
    """
    Ensure all *required_fields* appear in *headers*.

    Raises ``ValidationError`` listing missing columns.
    """
    missing = [f for f in required_fields if f not in headers]
    if missing:
        raise ValidationError(f"Missing required columns: {', '.join(missing)}")
    return True


def validate_batch_size(batch_size: int, max_batch: int = 1000) -> bool:
    """
    Validate a batch size is positive and within *max_batch*.

    Raises ``ValidationError`` on failure.
    """
    if batch_size <= 0:
        raise ValidationError("Batch size must be positive")
    if batch_size > max_batch:
        raise ValidationError(f"Batch size {batch_size} exceeds maximum {max_batch}")
    return True


# ---------------------------------------------------------------------------
# Date-of-birth / age helpers
# ---------------------------------------------------------------------------
def validate_date_of_birth(
    dob: Union[str, date],
    min_age: int = 2,
    max_age: int = 25,
) -> date:
    """
    Parse and validate a date of birth, returning the parsed ``date`` object.

    Raises ``ValidationError`` when the age is outside [min_age, max_age].
    """
    if isinstance(dob, str):
        try:
            dob = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD")

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    if age < min_age:
        raise ValidationError(f"Must be at least {min_age} years old")
    if age > max_age:
        raise ValidationError(f"Cannot be older than {max_age} years")

    return dob


# ---------------------------------------------------------------------------
# Choice validation (eliminates repeated ``[c[0] for c in X.CHOICES]`` blocks)
# ---------------------------------------------------------------------------
def validate_choice(value: str, choices, field_name: str = "value") -> bool:
    """
    Validate *value* is one of the first elements in a Django-style
    ``CHOICES`` tuple-list, e.g. ``[("active", "Active"), …]``.

    Raises ``ValidationError`` on failure.
    """
    valid_values = [c[0] for c in choices]
    if value not in valid_values:
        raise ValidationError(f"Invalid {field_name}: {value}")
    return True
