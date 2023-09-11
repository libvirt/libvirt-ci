# docker.py - module implementing docker container runtime wrapper logic
#
# Copyright (c) 2023 Abdulwasiu Apalowo.
#
# SPDX-License-Identifier: GPL-2.0-or-later

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

    def run(self, image, container_cmd, user, tempdir, env=None, datadir=None,
            script=None, **kwargs):
        """
        Prepares and runs the command inside a container.

        See Container.run() for more information.
        """

        return super().run(image, container_cmd, user, tempdir, env, datadir,
                           script, **kwargs)

    def _images(self):
        """
        Get all container images.

        :returns: a list of image details
        """

        img = super()._images()

        # Docker lacks proper JSON format output and instead of a single JSON
        # list object of all images it will return individual JSON objects
        # for all images, one per line
        images = [json.loads(image) for image in img.strip().split("\n") if image]

        log.debug(f"Deserialized {self.engine} images\n%s", images)
        return images

    def image_exists(self, image_ref, image_tag):
        """
        Check if image exists in docker.
        :param image_ref: name/id/registry-path of image to check (str).
        :param image_tag: image tag (str).

        :returns: boolean
        """

        for img in self._images():
            id = img.get("ID")
            img_repository = img.get("Repository")
            img_tag = img.get("Tag", "latest")

            if (image_ref and id.startswith(image_ref)) or (image_ref == img_repository and image_tag == img_tag):
                return True

        return False
