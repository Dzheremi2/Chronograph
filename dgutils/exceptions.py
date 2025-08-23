# pylint: disable=unnecessary-pass


class SingletonInstantiation(Exception):
    """Raised when a second instance of a singleton class is created."""

    pass


class FinalClassInherited(Exception):
    """Raised on subclassing a `@final` decorated class"""

    pass


class BaseClassInstantiation(Exception):
    """Raised on instantiation of a `@baseclass` decorated class"""

    pass
