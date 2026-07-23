"""Exceptions raised while parsing and encoding FIT files."""


class FitError(ValueError):
    """Base exception for FIT processing errors."""


class FitParseError(FitError):
    """Base exception for malformed FIT input."""


class FitHeaderError(FitParseError):
    """Raised when a FIT file header is malformed or truncated."""


class FitRecordError(FitParseError):
    """Raised when a FIT record cannot be decoded safely."""


class FitCRCError(FitParseError):
    """Raised when a FIT checksum does not match its payload."""


class FitEncodingError(FitError):
    """Raised when an in-memory FIT model cannot be encoded."""


class FitValidationError(FitEncodingError):
    """Raised when a FIT model violates protocol or profile rules."""
