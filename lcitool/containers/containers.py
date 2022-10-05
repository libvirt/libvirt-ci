import logging
import subprocess

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

    @staticmethod
    def _exec(command, _exception=ContainerError, **kwargs):
        """
        Execute command in a subprocess.run call.

        :param command: a list of command to run in the process
        :param _exception: an instance of ContainerError
        :param **kwargs: arguments passed to subprocess.run()

        :returns: an instance of subprocess.CompletedProcess
        """

        try:
            proc = subprocess.run(args=command, encoding="utf-8",
                                  **kwargs)
        except subprocess.CalledProcessError as ex:
            raise _exception(str(ex.returncode))

        return proc
