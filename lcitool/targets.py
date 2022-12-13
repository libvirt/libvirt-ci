# targets.py - module containing accessors to per-target information
#
# Copyright (C) 2022 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging

from lcitool import LcitoolError
from lcitool.inventory import Inventory as Targets   # noqa


log = logging.getLogger(__name__)


class TargetsError(LcitoolError):
    """Global exception type for the targets module."""

    def __init__(self, message):
        super().__init__(message, "Targets")


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
