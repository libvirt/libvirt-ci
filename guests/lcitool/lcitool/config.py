# config.py - module containing configuration file handling primitives
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import os
import yaml

from pathlib import Path
from pkg_resources import resource_filename

from lcitool.singleton import Singleton

log = logging.getLogger(__name__)


class ConfigError(Exception):
    """
    Global exception type for the config module.

    Contains a detailed message coming from one of its subclassed exception
    types. On the application level, this is the exception type you should be
    catching instead of the subclassed types.
    """

    def __str__(self):
        return f"Configuration error: {self.message}"


class LoadError(ConfigError):
    """Thrown when the configuration for lcitool could not be loaded."""

    def __init__(self, message):
        message_prefix = "Failed to load config: "
        self.message = message_prefix + message


class ValidationError(ConfigError):
    """Thrown when the configuration for lcitool could not be validated."""

    def __init__(self, message):
        message_prefix = "Failed to validate config: "
        self.message = message_prefix + message


class Config(metaclass=Singleton):

    def __init__(self):

        # Load the template config containing the defaults first, this must
        # always succeed.

        default_config = resource_filename(__name__, "etc/config.yml")
        with open(default_config, "r") as fp:
            self.values = yaml.safe_load(fp)

        user_config_path = None
        for fname in ["config.yml", "config.yaml"]:
            user_config_path = self._get_config_file(fname)

            if user_config_path.exists():
                break
        else:
            return

        user_config_path_str = user_config_path.as_posix()
        log.debug(f"Loading configuration from '{user_config_path_str}'")
        try:
            with open(user_config_path, "r") as fp:
                user_config = yaml.safe_load(fp)
        except Exception as e:
            raise LoadError(f"'{user_config_path.name}': {e}")

        if user_config is None:
            raise ValidationError(f"'{user_config_path.name}' is empty")

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
                log.debug(f"Removing unknown key '{k}' from config")

                del _dict[k]

    def _remove_all_unknown_keys(self, config):
        # remove keys we don't recognize
        self._remove_unknown_keys(config, self.values.keys())
        for section in self.values.keys():
            if section in config:
                self._remove_unknown_keys(config[section], self.values[section].keys())

    def _validate_section(self, section, mandatory_keys):
        log.debug(f"Validating section='[{section}]' "
                  f"against keys='{mandatory_keys}'")

        # check that the mandatory keys are present and non-empty
        for key in mandatory_keys:
            if self.values.get(section).get(key) is None:
                raise ValidationError(
                    f"Missing or empty value for mandatory key "
                    f"'{section}.{key}'"
                )

        # check that all keys have values assigned and of the right type
        for key in self.values[section].keys():

            # mandatory keys were already checked, so this covers optional keys
            if self.values[section][key] is None:
                raise ValidationError(f"Missing value for '{section}.{key}'")

            if not isinstance(self.values[section][key], (str, int)):
                raise ValidationError(f"Invalid type for key '{section}.{key}'")

    # Validate that parameters needed for VM install are present
    def validate_vm_settings(self):
        self._validate_section("install", ["root_password"])

        flavor = self.values["install"].get("flavor")
        if flavor not in ["test", "gitlab"]:
            raise ValidationError(
                f"Invalid value '{flavor}' for 'install.flavor'"
            )

        if flavor == "gitlab":
            self._validate_section("gitlab", ["runner_secret"])

    def _update(self, values):
        for section in self.values.keys():
            if section in values:
                log.debug(f"Applying user values: '{values[section]}'")

                self.values[section].update(values[section])
