# config.py - module containing configuration file handling primitives
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import yaml
from pathlib import Path

import lcitool.util as Util


class Config:

    def __init__(self):

        # Load the template config containing the defaults first, this must
        # always succeed.
        # NOTE: we should load this from /usr/share once we start packaging
        # lcitool
        base = Util.get_base()
        with open(Path(base, "configs", "config.yaml"), "r") as fp:
            self.values = yaml.safe_load(fp)

        user_config_path = self._get_config_file("config.yaml")
        if not user_config_path.exists():
            return

        try:
            with open(user_config_path, "r") as fp:
                user_config = yaml.safe_load(fp)
        except Exception as e:
            raise Exception("Invalid config.yaml file: {}".format(e))

        if user_config is None:
            raise Exception("Invalid config.yaml file")

        # delete user params we don't recognize
        self._remove_all_unknown_keys(user_config)

        # Override the default settings with user config
        self._update(user_config)

    @staticmethod
    def _get_config_file(name):
        try:
            config_dir = Path(os.environ["XDG_CONFIG_HOME"])
        except KeyError:
            config_dir = Path(os.environ["HOME"], ".config")

        return Path(config_dir, "lcitool", name)

    @staticmethod
    def _remove_unknown_keys(_dict, known_keys):
        keys = list(_dict.keys())

        for k in keys:
            if k not in known_keys:
                del _dict[k]

    def _remove_all_unknown_keys(self, config):
        # remove keys we don't recognize
        self._remove_unknown_keys(config, self.values.keys())
        for section in self.values.keys():
            if section in config:
                self._remove_unknown_keys(config[section], self.values[section].keys())

    def _validate_section(self, section, mandatory_keys):
        # check that the mandatory keys are present and non-empty
        for key in mandatory_keys:
            if self.values.get(section).get(key) is None:
                raise Exception(("Missing or empty value for mandatory key "
                                 "'{}.{}'").format(section, key))

        # check that all keys have values assigned and of the right type
        for key in self.values[section].keys():

            # mandatory keys were already checked, so this covers optional keys
            if self.values[section][key] is None:
                raise Exception(
                    "Missing value for '{}.{}'".format(section, key)
                )

            if not isinstance(self.values[section][key], (str, int)):
                raise Exception(
                    "Invalid type for key '{}.{}'".format(section, key)
                )

    # Validate that parameters needed for VM install are present
    def validate_vm_settings(self):
        self._validate_section("install", ["root_password"])

        flavor = self.values["install"].get("flavor")
        if flavor not in ["test", "gitlab"]:
            raise Exception(
                "Invalid value '{}' for 'install.flavor'".format(flavor)
            )

        if flavor == "gitlab":
            self._validate_section("gitlab", ["runner_secret"])

    def _update(self, values):
        for section in self.values.keys():
            if section in values:
                self.values[section].update(values[section])
