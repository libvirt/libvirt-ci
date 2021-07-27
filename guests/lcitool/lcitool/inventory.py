# inventory - module containing Ansible inventory handling primitives
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import copy
import logging
import yaml

from pathlib import Path
from pkg_resources import resource_filename

from lcitool import util
from lcitool.singleton import Singleton

log = logging.getLogger(__name__)


class InventoryError(Exception):
    """
    Global exception type for the inventory module.

    Functions/methods in this module will raise either this exception or its
    subclass on failure.
    On the application level, this is the exception type you should be catching.
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"Inventory error: {self.message}"


class Inventory(metaclass=Singleton):

    @property
    def target_facts(self):
        if self._target_facts is None:
            self._target_facts = self._load_target_facts()
        return self._target_facts

    @property
    def targets(self):
        return list(self.target_facts.keys())

    @property
    def ansible_inventory(self):
        if self._ansible_inventory is None:
            self._ansible_inventory = self._get_ansible_inventory()
        return self._ansible_inventory

    @property
    def hosts(self):
        def _findall_hosts_cb(ansible_host_facts):
            # Ansible's inventory is formatted as YAML, when we extract the
            # 'hosts' key, we get this:
            # {
            #  'host_1': {facts_1},
            #  'host_N': {facts_N}
            # }
            # and we need to convert it to this:
            # ['host_1', 'host_N']
            return ansible_host_facts.keys()

        # lazy evaluation
        if self._hosts is None:

            # a host may be part of several groups, but we need count it only once
            self._hosts = list(set(util.findall("hosts",
                                                self.ansible_inventory,
                                                cb=_findall_hosts_cb)))
        return self._hosts

    def __init__(self):
        self._target_facts = None
        self._ansible_inventory = None
        self._hosts = None

    @staticmethod
    def _read_facts_from_file(yaml_path):
        with open(yaml_path, "r") as infile:
            return yaml.safe_load(infile)

    def _get_ansible_inventory(self):
        from lcitool.ansible_wrapper import AnsibleWrapper

        inventory_path = Path(util.get_config_dir(), "inventory")
        inventory_path_str = inventory_path.as_posix()
        if not inventory_path.exists():
            raise InventoryError(
                f"Missing Ansible inventory '{inventory_path}'"
            )

        log.debug(f"Running ansible-inventory on '{inventory_path_str}'")
        ansible_runner = AnsibleWrapper()
        ansible_runner.prepare_env(inventory=inventory_path,
                                   group_vars=self.target_facts)
        inventory = ansible_runner.get_inventory()

        return inventory

    def _load_facts_from(self, facts_dir):
        facts = {}
        for entry in sorted(facts_dir.iterdir()):
            if not entry.is_file() or entry.suffix != ".yml":
                continue

            log.debug(f"Loading facts from '{entry}'")
            facts.update(self._read_facts_from_file(entry))

        return facts

    def _load_target_facts(self):
        facts = {}
        group_vars_path = Path(resource_filename(__name__, "ansible/group_vars/"))
        group_vars_all_path = Path(group_vars_path, "all")

        # first load the shared facts from group_vars/all
        shared_facts = self._load_facts_from(group_vars_all_path)

        # then load the rest of the facts
        for entry in group_vars_path.iterdir():
            if not entry.is_dir() or entry.name == "all":
                continue

            tmp = self._load_facts_from(entry)

            # override shared facts with per-distro facts
            target = entry.name
            facts[target] = copy.deepcopy(shared_facts)
            facts[target].update(tmp)

        return facts

    def _expand_pattern(self, pattern, iterable, name):
        try:
            return util.expand_pattern(pattern, iterable, name)
        except Exception as ex:
            raise InventoryError(f"Failed to expand '{pattern}': {ex}")

    def expand_hosts(self, pattern):
        return self._expand_pattern(pattern, self.hosts, "hosts")
