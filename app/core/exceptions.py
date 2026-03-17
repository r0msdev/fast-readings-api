"""Domain-level exceptions shared across all apps."""


class DuplicateResourceError(Exception):
    """Raised when an attempt is made to create a resource that already exists."""
