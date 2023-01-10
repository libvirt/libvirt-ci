import logging

from .containers import Container, ContainerError

log = logging.getLogger()


class PodmanBuildError(ContainerError):
    """
    Thrown whenever error occurs during
    podman build operation.
    """
    pass


class PodmanRunError(ContainerError):
    """
    Thrown whenever error occurs during
    podman run operation.
    """
    pass


class Podman(Container):
    """Podman container class"""

    def __init__(self):
        super().__init__()
        self._run_exception = PodmanRunError
        self._build_exception = PodmanBuildError
