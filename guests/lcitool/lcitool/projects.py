# projects.py - module containing per-project package mapping primitives
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import yaml

from pathlib import Path
from pkg_resources import resource_filename

from lcitool import util
from lcitool.singleton import Singleton

log = logging.getLogger(__name__)


class ProjectError(Exception):
    """
    Global exception type for the projects module.

    Functions/methods in this module will raise either this exception or its
    subclass on failure.
    On the application level, this is the exception type you should be
    catching.
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"Project error: {self.message}"


class Projects(metaclass=Singleton):

    def __init__(self):
        self._packages = self._load_projects()
        mappings_path = resource_filename(__name__,
                                          "ansible/vars/mappings.yml")

        try:
            with open(mappings_path, "r") as infile:
                mappings = yaml.safe_load(infile)
                self._mappings = mappings["mappings"]
                self._pypi_mappings = mappings["pypi_mappings"]
                self._cpan_mappings = mappings["cpan_mappings"]
        except Exception as ex:
            raise ProjectError(f"Can't load mappings: {ex}")

    @staticmethod
    def _load_projects():
        source = Path(resource_filename(__name__, "ansible/vars/projects"))

        packages = {}
        for item in source.iterdir():
            if not item.is_file() or item.suffix != ".yml":
                continue

            project = item.stem

            log.debug(f"Loading mappings for project '{project}'")
            try:
                with open(item, "r") as infile:
                    project_info = yaml.safe_load(infile)
                    packages[project] = project_info["packages"]
            except Exception as ex:
                raise ProjectError(f"Can't load packages for '{project}': {ex}")

        return packages

    def expand_pattern(self, pattern):
        try:
            projects_expanded = util.expand_pattern(pattern, self._packages,
                                                    "project")
        except Exception as ex:
            raise ProjectError(f"Failed to expand '{pattern}': {ex}")

        # Some projects are internal implementation details and should
        # not be exposed to the user
        internal_projects = {
            "base",
            "cloud-init",
            "developer",
            "perl-cpan",
            "python-pip",
            "unwanted",
            "vm",
        }

        return list(projects_expanded - internal_projects)

    def get_mappings(self):
        return self._mappings

    def get_pypi_mappings(self):
        return self._pypi_mappings

    def get_cpan_mappings(self):
        return self._cpan_mappings

    def get_packages(self, project):
        return self._packages[project]


class Project:
    """
    Attributes:
        :ivar name: project name
        :ivar generic_packages: list of generic packages needed by the project
                                to build successfully
    """

    @property
    def generic_packages(self):
        return self._generic_packages

    def __init__(self, name):
        self.name = name
        self._generic_packages = None
