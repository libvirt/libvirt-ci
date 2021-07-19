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
    """
    Attributes:
        :ivar names: list of all project names
    """

    @property
    def names(self):
        return list(self._projects.keys())

    @property
    def mappings(self):

        # lazy load mappings
        if self._mappings is None:
            self._load_mappings()
        return self._mappings

    @property
    def pypi_mappings(self):

        # lazy load mappings
        if self._pypi_mappings is None:
            self._load_mappings()
        return self._pypi_mappings

    @property
    def cpan_mappings(self):

        # lazy load mappings
        if self._cpan_mappings is None:
            self._load_mappings()
        return self._cpan_mappings

    def __init__(self):
        self._projects = self._load_projects()
        self._mappings = None
        self._pypi_mappings = None
        self._cpan_mappings = None

    @staticmethod
    def _load_projects():
        source = Path(resource_filename(__name__, "ansible/vars/projects"))

        projects = {}
        for item in source.iterdir():
            if not item.is_file() or item.suffix != ".yml":
                continue

            projects[item.stem] = Project(item.stem)
        return projects

    def _load_mappings(self):
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

    def expand_pattern(self, pattern):
        try:
            projects_expanded = util.expand_pattern(pattern, self.names,
                                                    "project")
        except Exception as ex:
            raise ProjectError(f"Failed to expand '{pattern}': {ex}")

        # Some projects are internal implementation details and should
        # not be exposed to the user
        internal_projects = [
            "base",
            "cloud-init",
            "developer",
            "perl-cpan",
            "python-pip",
            "unwanted",
            "vm",
        ]
        for project in internal_projects:
            if project in projects_expanded:
                projects_expanded.remove(project)

        return list(projects_expanded)

    def get_packages(self, project):
        return self._projects[project].generic_packages


class Project:
    """
    Attributes:
        :ivar name: project name
        :ivar generic_packages: list of generic packages needed by the project
                                to build successfully
    """

    @property
    def generic_packages(self):

        # lazy evaluation: load per-project mappings when we actually need them
        if self._generic_packages is None:
            self._generic_packages = self._load_generic_packages()
        return self._generic_packages

    def __init__(self, name):
        self.name = name
        self._generic_packages = None

    def _load_generic_packages(self):
        log.debug(f"Loading generic package list for project '{self.name}'")

        tmp = Path(resource_filename(__name__, "ansible/vars/projects"))
        yaml_path = Path(tmp, self.name + ".yml")

        try:
            with open(yaml_path, "r") as infile:
                yaml_packages = yaml.safe_load(infile)
                return yaml_packages["packages"]
        except Exception as ex:
            raise ProjectError(f"Can't load packages for '{self.name}': {ex}")
