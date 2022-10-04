import shutil
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

    def _check(self):
        """
        Checks that engine is available and running. It
        does this by running "{/path/to/engine} version"
        to check if the engine is available

        Returns
             True: if the path can be found and the
                   engine is available.
             False: if the path can not be found OR
                    if the path can be found AND
                      the engine is not running OR
                      the engine's background process is not
                      well set up.
        """

        message = f"Checking if '{self.engine}' is available...%s"

        command = shutil.which(self.engine)
        if command is None:
            log.debug(message, f"no\n'{self.engine}' path cannot be found")
            return False

        exists = self._exec([command, "version"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
        if exists.returncode:
            log.debug(message, "no")
        else:
            log.debug(message, "yes")

        log.debug("\n" + exists.stdout)
        return not exists.returncode

    @property
    def available(self):
        """
        Checks whether the container engine is available and ready to use.

        :returns: boolean
        """

        return self._check()
