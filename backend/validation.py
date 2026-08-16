"""Configuration validation utilities."""

import re
from urllib.parse import urlparse


def validate_url(url: str, permitted_schemes=None) -> str:
    """Validate and normalize a URL.

    Returns normalized URL string or raises ValidationError.
    """
    from usr.plugins.honcho_shared_memory.backend.exceptions import ValidationError

    if not url or not isinstance(url, str):
        raise ValidationError("URL is required")

    url = url.strip()
    if not url:
        raise ValidationError("URL is required")

    # Ensure scheme is present
    if "://" not in url:
        url = "http://" + url

    parsed = urlparse(url)

    if permitted_schemes is None:
        permitted_schemes = {"http", "https"}

    if parsed.scheme not in permitted_schemes:
        raise ValidationError(
            f"Unsupported URL scheme: {parsed.scheme}. Use http or https."
        )

    # Reject control characters
    if re.search(r"[\x00-\x1f\x7f]", url):
        raise ValidationError("URL contains control characters")

    # Reject local file schemes
    if parsed.scheme in ("file", "ftp"):
        raise ValidationError(f"Unsupported URL scheme: {parsed.scheme}")

    # Normalize: remove trailing slashes for base URLs
    if not parsed.path or parsed.path == "/":
        url = f"{parsed.scheme}://{parsed.netloc}"
    else:
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"

    return url


def validate_identifier(value: str, field_name: str) -> str:
    """Validate workspace/peer/agent identifiers.

    Allowed: ASCII alphanumeric, underscore, hyphen, dot.
    Rejected: empty, control characters, whitespace.
    """
    from usr.plugins.honcho_shared_memory.backend.exceptions import ValidationError

    if not value or not isinstance(value, str):
        raise ValidationError(f"{field_name} is required")

    value = value.strip()
    if not value:
        raise ValidationError(f"{field_name} cannot be empty")

    if re.search(r"[\x00-\x1f\x7f]", value):
        raise ValidationError(f"{field_name} contains control characters")

    if re.search(r"\s", value):
        raise ValidationError(f"{field_name} contains whitespace")

    # Allow common identifier characters
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", value):
        raise ValidationError(
            f"{field_name} contains invalid characters (only a-z, A-Z, 0-9, _, -, . allowed)"
        )

    return value


def validate_int_range(value, min_val: int, max_val: int, field_name: str) -> int:
    """Validate integer is within range."""
    from usr.plugins.honcho_shared_memory.backend.exceptions import ValidationError

    if value is None:
        raise ValidationError(f"{field_name} is required")

    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be an integer")

    if value < min_val or value > max_val:
        raise ValidationError(f"{field_name} must be between {min_val} and {max_val}")

    return value


def validate_agent_ids(ids: list, current_agent_id: str):
    """Validate allowed agent IDs list."""
    from usr.plugins.honcho_shared_memory.backend.exceptions import ValidationError

    if not ids:
        return

    seen = set()
    for aid in ids:
        if not aid or not isinstance(aid, str):
            raise ValidationError("Agent ID cannot be empty")
        aid = aid.strip()
        if not aid:
            raise ValidationError("Agent ID cannot be empty")
        validate_identifier(aid, "Agent ID")
        if aid in seen:
            raise ValidationError(f"Duplicate agent ID: {aid}")
        seen.add(aid)
