import logging

from lcitool import LcitoolError

log = logging.getLogger(__name__)


class InstallerError(LcitoolError):
    def __init__(self, message):
        super().__init__(message, "Installer")


class VirtInstall:

    def run(self, name, facts, wait=False):
        """
        Kick off the VM installation.

        :param name: name for the VM instance (str)
        :param facts: host facts for this OS instance (dict)
        :param wait: whether to wait for the installation to complete (boolean)
        """

        pass
