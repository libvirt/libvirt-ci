import logging

from abc import ABC

log = logging.getLogger()


class Container(ABC):
    """Abstract class for containers"""

    def __init__(self):
        if self.__class__ is Container:
            self.engine = None
        else:
            self.engine = self.__class__.__name__.lower()
