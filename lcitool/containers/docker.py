import logging

from .containers import Container, ContainerError

log = logging.getLogger()


class DockerBuildError(ContainerError):
    """
    Thrown whenever error occurs during
    docker build operation.
    """
    pass


class DockerRunError(ContainerError):
    """
    Thrown whenever error occurs during
    docker run operation.
    """
    pass


class Docker(Container):
    """Docker container class"""

    def __init__(self):
        super().__init__()
        self._run_exception = DockerRunError
        self._build_exception = DockerBuildError
