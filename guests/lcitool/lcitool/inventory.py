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
from lcitool.singleton import Singleton

log = logging.getLogger(__name__)


class Inventory(metaclass=Singleton):

    def __init__(self):
        ansible_cfg_path = resource_filename(__name__, "ansible/ansible.cfg")

        try:
            parser = configparser.ConfigParser()
            parser.read(ansible_cfg_path)
            inventory_path = parser.get("defaults", "inventory")
        except Exception as ex:
            raise Exception(
                f"Can't read inventory location in ansible.cfg: {ex}"
            )

        posix_path = Path("ansible", inventory_path).as_posix()
        inventory_path = resource_filename(__name__, posix_path)
        self._facts = {}

        log.debug(f"Loading inventory '{inventory_path}'")
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
                f"Missing or invalid inventory ({inventory_path}): {ex}"
            )

        for host in self._facts:
            try:
                self._facts[host] = self._read_all_facts(host)
                self._facts[host]["inventory_hostname"] = host
            except Exception as ex:
                raise Exception(f"Can't load facts for '{host}': {ex}")

    @staticmethod
    def _add_facts_from_file(facts, yaml_path):
        with open(yaml_path, "r") as infile:
            some_facts = yaml.safe_load(infile)
            for fact in some_facts:
                facts[fact] = some_facts[fact]

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

    def expand_pattern(self, pattern):
        return list(util.expand_pattern(pattern, self._facts, "host"))

    def get_facts(self, host):
        return self._facts[host]
