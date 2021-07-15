# inventory - module containing Ansible inventory handling primitives
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import configparser
import logging
import yaml

from pathlib import Path
from pkg_resources import resource_filename

from lcitool import util
from lcitool.ansible_wrapper import AnsibleWrapper
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
    def facts(self):

        # lazy evaluation
        if self._facts is None:
            self._facts = self._load_facts()
        return self._facts

    @property
    def targets(self):

        # lazy evaluation
        if self._targets is None:
            self._targets = list(self.facts.keys())
        return self._targets

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
        self._facts = None
        self._targets = None
        self._ansible_inventory = None
        self._hosts = None

    @staticmethod
    def _add_facts_from_file(facts, yaml_path):
        with open(yaml_path, "r") as infile:
            some_facts = yaml.safe_load(infile)
            for fact in some_facts:
                facts[fact] = some_facts[fact]

    def _get_ansible_inventory(self):
        ansible_dir = resource_filename(__name__, "ansible")
        inventory_path = Path(ansible_dir, "inventory")

        log.debug(f"Running ansible-inventory on '{inventory_path}'")
        ansible_runner = AnsibleWrapper()
        ansible_runner.prepare_env(inventory=inventory_path,
                                   host_vars=self.facts)
        inventory = ansible_runner.get_inventory()

        return inventory

    def _read_all_facts(self, host):
        sources = [
            resource_filename(__name__, "ansible/group_vars/all"),
            resource_filename(__name__, f"ansible/host_vars/{host}")
        ]

        facts = {}

        # We load from group_vars/ first and host_vars/ second, sorting
        # files alphabetically; doing so should result in our view of
        # the facts matching Ansible's
        for source in sources:
            for item in sorted(Path(source).iterdir()):
                yaml_path = Path(source, item)
                if not yaml_path.is_file():
                    continue
                if yaml_path.suffix != ".yml":
                    continue

                log.debug(f"Loading facts from '{yaml_path}'")
                self._add_facts_from_file(facts, yaml_path)

        return facts

    def _load_facts(self):
        ansible_cfg_path = resource_filename(__name__, "ansible/ansible.cfg")

        try:
            parser = configparser.ConfigParser()
            parser.read(ansible_cfg_path)
            inventory_path = parser.get("defaults", "inventory")
        except Exception as ex:
            msg = f"Can't read inventory location in ansible.cfg: {ex}"
            raise InventoryError(msg) from ex

        posix_path = Path("ansible", inventory_path).as_posix()
        inventory_path = resource_filename(__name__, posix_path)
        facts = {}

        log.debug(f"Loading inventory '{inventory_path}'")
        try:
            # We can only deal with trivial inventories, but that's
            # all we need right now and we can expand support further
            # later on if necessary
            with open(inventory_path, "r") as infile:
                for line in infile:
                    host = line.strip()
                    facts[host] = {}
        except Exception as ex:
            msg = f"Missing or invalid inventory ({inventory_path}): {ex}"
            raise InventoryError(msg) from ex

        for host in facts:
            try:
                facts[host] = self._read_all_facts(host)
                facts[host]["inventory_hostname"] = host
            except Exception as ex:
                msg = f"Can't load facts for '{host}': {ex}"
                raise InventoryError(msg) from ex
        return facts

    def _expand_pattern(self, pattern, iterable, name):
        try:
            return list(util.expand_pattern(pattern, iterable, name))
        except Exception as ex:
            raise InventoryError(f"Failed to expand '{pattern}': {ex}")

    def expand_hosts(self, pattern):
        return self._expand_pattern(pattern, self.hosts, "hosts")

    def has_host(self, host):
        return host in self.facts

    def get_facts(self, target):
        try:
            return self.facts[target]
        except KeyError:
            raise InventoryError(f"Invalid target '{target}'")
