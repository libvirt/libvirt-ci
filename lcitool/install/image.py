# image.py - manages downloaded vendor OS images
#
# Copyright (C) 2023 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import yaml

from collections import UserDict
from pathlib import Path

from lcitool import util, LcitoolError

log = logging.getLogger(__name__)


class ImageError(LcitoolError):
    def __init__(self, message):
        super().__init__(message, "Image")


class MetadataLoadError(ImageError):
    """Thrown when metadata for an image could not be loaded"""


class MetadataValidationError(ImageError):
    """Thrown when image metadata validation fails"""


class Metadata(UserDict):
    @staticmethod
    def _validate(dict_):
        schema = set(["target", "image", "url", "arch", "format",
                      "libosinfo_id"])
        actual = set(dict_.keys())
        if actual != schema:
            raise ValueError(actual - schema)

    def load(self, file):
        # load image metadata
        with open(file, 'r') as f:
            try:
                m = yaml.safe_load(f)
            except Exception as ex:
                raise MetadataLoadError(ex)

            try:
                self._validate(m)
            except ValueError as e:
                invalid_keys = list(e.args)
                raise MetadataValidationError(
                    f"Metadata schema validation failed on '{f.name}', "
                    f"violating keys: {invalid_keys}"
                )
            self.update(m)
        return self

    def dump(self, file):
        pass


class Images():
    @staticmethod
    def _get_cache_dir():
        cache_dir = Path(util.get_cache_dir(), "images")
        if not cache_dir.exists():
            cache_dir.mkdir()
        return cache_dir

    def __init__(self):
        self._cache_dir = self._get_cache_dir()
        self._osinfodb = None
        self._target_images = None


class Image:
    """
    Attributes:
        :ivar name: name of the image (None until the image is downloaded)
        :ivar path: path to the image (None until the image is downloaded)
        :ivar metadata: metadata for this image (as dict)
    """

    def __init__(self, metadata, download_dir):
        """
        Instantiates a base image handler.

        :param metadata: metadata for this disk image
        :param download_dir: base directory where the image should be
                             downloaded to
        """

        self._metadata = metadata
        self._download_dir = download_dir

    @property
    def name(self):
        if self.path:
            return self.path.name
        return None

    @property
    def path(self):
        val = self._metadata.get("image")
        if val:
            return Path(val)
        return None

    @property
    def metadata(self):
        return self._metadata

    def download(self):
        pass
