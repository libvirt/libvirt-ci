# targets.py - module containing accessors to per-target information
#
# Copyright (C) 2022 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging

log = logging.getLogger(__name__)


class Target:
    """
    Attributes:
        :ivar _inventory: inventory used to retrieve the target facts
        :ivar name: target name
        :ivar cross_arch: cross compilation architecture
    """

    def __init__(self, inventory, name, cross_arch=None):
        self._inventory = inventory
        self.name = name
        self.cross_arch = cross_arch

    def __str__(self):
        if self.cross_arch:
            return f"{self.name} (cross_arch={self.cross_arch}"
        else:
            return self.name

    @property
    def facts(self):
        return self._inventory.target_facts[self.name]
