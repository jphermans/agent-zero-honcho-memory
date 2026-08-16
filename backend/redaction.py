"""Secret-redaction utilities for Honcho plugin output.

Never log or store raw credentials, tokens, or connection strings.
"""

import re
from typing import Callable

# Patterns for redaction (case-insensitive)
REDACT_PATTERNS: list[tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]]] = [
    (
        re.compile(
            r"(?i)authorization\s*[:=]\s*.+$",
        ),
        "Authorization: [REDACTED]",
    ),
    (
        re.compile(
            r"(?:bearer|token|api[-_]?key)\s*[:=]?\s*[^\s,;]+",
            re.IGNORECASE,
        ),
        "token: [REDACTED]",
    ),
    (
        re.compile(
            r"(?:password|passwd|pwd)\s*[:=]\s*[^\s,;]+",
            re.IGNORECASE,
        ),
        "password: [REDACTED]",
    ),
    (
        re.compile(
            r"postgres(?:ql)?://[^@]*:([^@]+)@",
            re.IGNORECASE,
        ),
        lambda m: m.group(0).replace(m.group(1), "[REDACTED]"),
    ),
    (
        re.compile(
            r"mongodb(?:\+srv)?://[^@]*:([^@]+)@",
            re.IGNORECASE,
        ),
        lambda m: m.group(0).replace(m.group(1), "[REDACTED]"),
    ),
    (
        re.compile(
            r"redis://[^@]*:([^@]+)@",
            re.IGNORECASE,
        ),
        lambda m: m.group(0).replace(m.group(1), "[REDACTED]"),
    ),
    (
        re.compile(
            r"-+BEGIN [^-]+ PRIVATE KEY-+",
            re.IGNORECASE,
        ),
        "[PRIVATE KEY REDACTED]",
    ),
    (
        re.compile(
            r"-+END [^-]+ PRIVATE KEY-+",
            re.IGNORECASE,
        ),
        "[PRIVATE KEY REDACTED]",
    ),
]


def redact_text(text: str) -> str:
    """Replace secrets in the given string with [REDACTED] placeholders."""
    if not text:
        return text

    for pattern, replacement in REDACT_PATTERNS:
        if callable(replacement):
            text = pattern.sub(replacement, text)
        else:
            text = pattern.sub(replacement, text)
    return text


def redact_headers(headers: dict) -> dict:
    """Return a copy of the header dict with secrets masked."""
    if not headers:
        return {}
    masked = {}
    sensitive_keys = {"authorization", "x-api-key", "cookie", "set-cookie"}
    for k, v in headers.items():
        if k.lower() in sensitive_keys:
            masked[k] = "[REDACTED]"
        else:
            masked[k] = v
    return masked


def contains_likely_secret(text: str) -> bool:
    """Returns True if the text likely contains credentials.

    This is a conservative heuristic for pre-storage filtering.
    """
    if not text:
        return False

    lower = text.lower()
    secret_indicators = [
        "api_key=",
        "apikey=",
        "api-key=",
        "api-key:",
        "password=",
        "password:",
        "token=",
        "token:",
        "secret=",
        "secret:",
        "authorization:",
        "bearer ",
        "-----begin",
        "-----end",
    ]
    return any(ind in lower for ind in secret_indicators)
