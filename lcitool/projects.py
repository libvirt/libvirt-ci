# projects.py - module containing per-project package mapping primitives
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import yaml

from pathlib import Path
from pkg_resources import resource_filename

from lcitool import util, LcitoolError
from lcitool.package import PackageFactory, PyPIPackage, CPANPackage

log = logging.getLogger(__name__)


class ProjectError(LcitoolError):
    """
    Global exception type for the projects module.

    Functions/methods in this module will raise either this exception or its
    subclass on failure.
    """

    def __init__(self, message):
        super().__init__(message, "Project")


class Projects:
    """
    Attributes:
        :ivar names: list of all project names
        :ivar public: dictionary from project names to ``Project`` objects for public projects
        :ivar internal: dictionary from project names to ``Project`` objects for internal projects
    """

    @property
    def public(self):
        if self._public is None:
            self._load_public()
        return self._public

    @property
    def names(self):
        return list(self.public.keys())

    @property
    def internal(self):
        if self._internal is None:
            self._load_internal()
        return self._internal

    @property
    def mappings(self):

        # lazy load mappings
        if self._mappings is None:
            self._mappings = self._load_mappings()
        return self._mappings

    def __init__(self):
        self._public = None
        self._internal = None
        self._mappings = None

    def _load_projects_from_path(self, path):
        projects = {}

        for item in path.iterdir():
            if not item.is_file() or item.suffix != ".yml":
                continue

            projects[item.stem] = Project(self, item.stem, item)

        return projects

    def _load_public(self):
        source = Path(resource_filename(__name__, "facts/projects"))
        projects = self._load_projects_from_path(source)

        if util.get_extra_data_dir() is not None:
            source = Path(util.get_extra_data_dir()).joinpath("projects")
            projects.update(self._load_projects_from_path(source))

        self._public = projects

    def _load_internal(self):
        source = Path(resource_filename(__name__, "facts/projects/internal"))
        self._internal = self._load_projects_from_path(source)

    def _load_mappings(self):
        mappings_path = resource_filename(__name__,
                                          "facts/mappings.yml")

        try:
            with open(mappings_path, "r") as infile:
                return yaml.safe_load(infile)
        except Exception as ex:
            log.debug("Can't load mappings")
            raise ProjectError(f"Can't load mappings: {ex}")

    def expand_names(self, pattern):
        try:
            return util.expand_pattern(pattern, self.names, "project")
        except Exception as ex:
            log.debug(f"Failed to expand '{pattern}'")
            raise ProjectError(f"Failed to expand '{pattern}': {ex}")

    def get_packages(self, projects, target):
        packages = {}

        for proj in projects:
            try:
                obj = self.public[proj]
            except KeyError:
                obj = self.internal[proj]
            packages.update(obj.get_packages(target))

        return packages

    def eval_generic_packages(self, target, generic_packages):
        pkgs = {}
        factory = PackageFactory(self.mappings, target.facts)
        needs_pypi = False
        needs_cpan = False

        for mapping in generic_packages:
            pkg = factory.get_package(mapping, target)
            if pkg is None:
                continue
            pkgs[pkg.mapping] = pkg

            if isinstance(pkg, PyPIPackage):
                needs_pypi = True
            elif isinstance(pkg, CPANPackage):
                needs_cpan = True

        # The get_packages eval_generic_packages cycle is deliberate and
        # harmless since we'll only ever hit it with the following internal
        # projects
        if needs_pypi:
            proj = self.internal["python-pip"]
            pkgs.update(proj.get_packages(target))
        if needs_cpan:
            proj = self.internal["perl-cpan"]
            pkgs.update(proj.get_packages(target))

        return pkgs


class Project:
    """
    Attributes:
        :ivar name: project name
        :ivar generic_packages: list of generic packages needed by the project
                                to build successfully
        :ivar projects: parent ``Projects`` instance
    """

    @property
    def generic_packages(self):

        # lazy evaluation: load per-project generic package list when we actually need it
        if self._generic_packages is None:
            self._generic_packages = self._load_generic_packages()
        return self._generic_packages

    def __init__(self, projects, name, path):
        self.projects = projects
        self.name = name
        self.path = path
        self._generic_packages = None
        self._target_packages = {}

    def _load_generic_packages(self):
        log.debug(f"Loading generic package list for project '{self.name}'")

        try:
            with open(self.path, "r") as infile:
                yaml_packages = yaml.safe_load(infile)
                return yaml_packages["packages"]
        except Exception as ex:
            log.debug(f"Can't load pacakges for '{self.name}'")
            raise ProjectError(f"Can't load packages for '{self.name}': {ex}")

    def get_packages(self, target):
        osname = target.facts["os"]["name"]
        osversion = target.facts["os"]["version"]
        target_name = f"{osname.lower()}-{osversion.lower()}"
        if target.cross_arch is None:
            target_name = f"{target_name}-x86_64"
        else:
            try:
                util.validate_cross_platform(target.cross_arch, osname)
            except ValueError as ex:
                raise ProjectError(ex)
            target_name = f"{target_name}-{target.cross_arch}"

        # lazy evaluation + caching of package names for a given distro
        if self._target_packages.get(target_name) is None:
            self._target_packages[target_name] = self.projects.eval_generic_packages(target,
                                                                                     self.generic_packages)
        return self._target_packages[target_name]
