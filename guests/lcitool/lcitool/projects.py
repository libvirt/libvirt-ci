# projects.py - module containing per-project package mapping primitives
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import yaml
from pathlib import Path

from lcitool import util


class Projects:

    def __init__(self):
        base = Path(util.get_base(), "ansible")

        mappings_path = Path(base, "vars", "mappings.yml")

        try:
            with open(mappings_path, "r") as infile:
                mappings = yaml.safe_load(infile)
                self._mappings = mappings["mappings"]
                self._pypi_mappings = mappings["pypi_mappings"]
                self._cpan_mappings = mappings["cpan_mappings"]
        except Exception as ex:
            raise Exception("Can't load mappings: {}".format(ex))

        source = Path(base, "vars", "projects")

        self._packages = {}
        for item in source.iterdir():
            yaml_path = Path(source, item)
            if not yaml_path.is_file():
                continue
            if yaml_path.suffix != ".yml":
                continue

            project = item.stem

            try:
                with open(yaml_path, "r") as infile:
                    packages = yaml.safe_load(infile)
                    self._packages[project] = packages["packages"]
            except Exception as ex:
                raise Exception(
                    "Can't load packages for '{}': {}".format(project, ex))

    def expand_pattern(self, pattern):
        projects = util.expand_pattern(pattern, self._packages, "project")

        # Some projects are internal implementation details and should
        # not be exposed to the user
        for project in ["base", "unwanted", "cloud-init"]:
            if project in projects:
                projects.remove(project)

        return projects

    def get_mappings(self):
        return self._mappings

    def get_pypi_mappings(self):
        return self._pypi_mappings

    def get_cpan_mappings(self):
        return self._cpan_mappings

    def get_packages(self, project):
        return self._packages[project]
