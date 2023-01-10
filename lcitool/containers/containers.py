import logging

from abc import ABC

from lcitool import LcitoolError

log = logging.getLogger()


class ContainerError(LcitoolError):
    """Global exception type for this module."""

    def __init__(self, message):
        super().__init__(self)
        self.message = self.__class__.__name__ + ": " + message


class Container(ABC):
    """Abstract class for containers"""

    def __init__(self):
        if self.__class__ is Container:
            self.engine = None
        else:
            self.engine = self.__class__.__name__.lower()

        self._run_exception = None
        self._build_exception = None
