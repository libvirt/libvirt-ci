import json
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

    def _images(self):
        """
        Get all container images.

        :returns: a list of image details
        """

        img = super()._images()

        # Docker lacks proper JSON format output and instead of a single JSON
        # list object of all images it will return individual JSON objects
        # for all images, one per line
        images = [json.loads(image) for image in img.strip().split("\n")]

        log.debug(f"Deserialized {self.engine} images\n%s", images)
        return images
