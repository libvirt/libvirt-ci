# targets.py - module containing accessors to per-target information
#
# Copyright (C) 2022 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import yaml

from pathlib import Path
from pkg_resources import resource_filename

from lcitool import util, LcitoolError


log = logging.getLogger(__name__)


class TargetsError(LcitoolError):
    """Global exception type for the targets module."""

    def __init__(self, message):
        super().__init__(message, "Targets")


class Targets():

    @property
    def target_facts(self):
        if self._target_facts is None:
            self._target_facts = self._load_target_facts()
        return self._target_facts

    @property
    def targets(self):
        return list(self.target_facts.keys())

    def __init__(self):
        self._target_facts = None

    @staticmethod
    def _read_facts_from_file(yaml_path):
        log.debug(f"Loading facts from '{yaml_path}'")
        with open(yaml_path, "r") as infile:
            return yaml.safe_load(infile)

    @staticmethod
    def _validate_target_facts(target_facts, target):
        fname = target + ".yml"

        actual_osname = target_facts["os"]["name"].lower()
        if not target.startswith(actual_osname + "-"):
            raise TargetsError(f'OS name "{target_facts["os"]["name"]}" does not match file name {fname}')
        target = target[len(actual_osname) + 1:]

        actual_version = target_facts["os"]["version"].lower()
        expected_version = target.replace("-", "")
        if expected_version != actual_version:
            raise TargetsError(f'OS version "{target_facts["os"]["version"]}" does not match version in file name {fname} ({expected_version})')

    def _load_target_facts(self):
        facts = {}
        targets_path = Path(resource_filename(__name__, "facts/targets/"))
        targets_all_path = Path(targets_path, "all.yml")

        # first load the shared facts from targets/all.yml
        shared_facts = self._read_facts_from_file(targets_all_path)

        # then load the rest of the facts
        for entry in targets_path.iterdir():
            if not entry.is_file() or entry.suffix != ".yml" or entry.name == "all.yml":
                continue

            target = entry.stem
            facts[target] = self._read_facts_from_file(entry)
            self._validate_target_facts(facts[target], target)
            facts[target]["target"] = target

            # missing per-distro facts fall back to shared facts
            util.merge_dict(shared_facts, facts[target])

        return facts


class BuildTarget:
    """
    Attributes:
        :ivar _targets: object to retrieve the target facts
        :ivar name: target name
        :ivar cross_arch: cross compilation architecture
    """

    def __init__(self, targets, packages, name, cross_arch=None):
        if name not in targets.target_facts:
            raise TargetsError(f"Target not found: {name}")
        self._packages = packages
        self.name = name
        self.cross_arch = cross_arch
        self.facts = targets.target_facts[self.name]

    def __str__(self):
        if self.cross_arch:
            return f"{self.name} (cross_arch={self.cross_arch}"
        else:
            return self.name

    def get_package(self, name):
        return self._packages.get_package(name, self)
