"""Typed plugin exceptions for Honcho Shared Memory."""


class HonchoPluginError(Exception):
    """Base exception for Honcho plugin."""

    pass


class ConfigurationError(HonchoPluginError):
    """Invalid or missing configuration."""

    pass


class AuthenticationError(HonchoPluginError):
    """Honcho authentication failure."""

    pass


class ConnectionError(HonchoPluginError):
    """Cannot reach the Honcho server."""

    pass


class TimeoutError(HonchoPluginError):
    """Request to Honcho timed out."""

    pass


class WorkspaceNotFoundError(HonchoPluginError):
    """Configured workspace does not exist."""

    pass


class PeerNotFoundError(HonchoPluginError):
    """Configured peer not found."""

    pass


class PermissionError(HonchoPluginError):
    """Insufficient permissions on Honcho."""

    pass


class ValidationError(HonchoPluginError):
    """Input validation failure."""

    pass


class APICompatibilityError(HonchoPluginError):
    """Honcho API version not supported."""

    pass


class RateLimitError(HonchoPluginError):
    """Honcho rate limit exceeded."""

    pass
