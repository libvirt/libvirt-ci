# inventory - module containing Ansible inventory handling primitives
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import configparser
import yaml
from pathlib import Path

import lcitool.util as Util


class Inventory:

    def __init__(self):
        base = Path(Util.get_base(), "ansible")
        ansible_cfg_path = Path(base, "ansible.cfg")

        try:
            parser = configparser.ConfigParser()
            parser.read(ansible_cfg_path)
            inventory_path = parser.get("defaults", "inventory")
        except Exception as ex:
            raise Exception(
                "Can't read inventory location in ansible.cfg: {}".format(ex))

        inventory_path = Path(base, inventory_path)

        self._facts = {}
        try:
            # We can only deal with trivial inventories, but that's
            # all we need right now and we can expand support further
            # later on if necessary
            with open(inventory_path, "r") as infile:
                for line in infile:
                    host = line.strip()
                    self._facts[host] = {}
        except Exception as ex:
            raise Exception(
                "Missing or invalid inventory ({}): {}".format(
                    inventory_path, ex
                )
            )

        for host in self._facts:
            try:
                self._facts[host] = self._read_all_facts(host)
                self._facts[host]["inventory_hostname"] = host
            except Exception as ex:
                raise Exception("Can't load facts for '{}': {}".format(
                    host, ex))

    @staticmethod
    def _add_facts_from_file(facts, yaml_path):
        with open(yaml_path, "r") as infile:
            some_facts = yaml.safe_load(infile)
            for fact in some_facts:
                facts[fact] = some_facts[fact]

    def _read_all_facts(self, host):
        base = Path(Util.get_base(), "ansible")

        sources = [
            Path(base, "group_vars", "all"),
            Path(base, "host_vars", host),
        ]

        facts = {}

        # We load from group_vars/ first and host_vars/ second, sorting
        # files alphabetically; doing so should result in our view of
        # the facts matching Ansible's
        for source in sources:
            for item in sorted(source.iterdir()):
                yaml_path = Path(source, item)
                if not yaml_path.is_file():
                    continue
                if yaml_path.suffix != ".yml":
                    continue
                self._add_facts_from_file(facts, yaml_path)

        return facts

    def expand_pattern(self, pattern):
        return Util.expand_pattern(pattern, self._facts, "host")

    def get_facts(self, host):
        return self._facts[host]
