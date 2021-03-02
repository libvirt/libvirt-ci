# ansible_wrapper.py - module abstracting the official Ansible runner module
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import ansible_runner
import logging

from pathlib import Path
from tempfile import TemporaryDirectory

from lcitool import util

log = logging.getLogger(__name__)


class AnsibleWrapperError(Exception):
    """Global exception type for this module.

    Contains a detailed message coming from one of its subclassed exception
    types. On the application level, this is the exception type you should be
    catching.
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"AnsibleWrapper error: {self.message}"


class ExecutionError(AnsibleWrapperError):
    """Thrown whenever the Ansible runner failed the execution."""

    def __init__(self, message):
        message_prefix = "Ansible execution failed: "
        self.message = message_prefix + message


class AnsibleWrapper():
    def __init__(self):
        self._tempdir = TemporaryDirectory(prefix="ansible_runner",
                                           dir=util.get_temp_dir())
        self._private_data_dir = Path(self._tempdir.name)

    def _get_default_params(self):
        default_params = {
            "private_data_dir": self._private_data_dir,
            "envvars": {
                # Group names officially cannot contain dashes, because those
                # characters are invalid in Python identifiers and it caused
                # issues in some Ansible scenarios like using the dot notation,
                # e.g. groups.group-with-dash. In simple group names like
                # ours dashes are still perfectly fine, so ignore the warning
                "ANSIBLE_TRANSFORM_INVALID_GROUP_CHARS": "ignore",
            }
        }

        return default_params

    def _run(self, params, **kwargs):
        """
        The actual entry point into the AnsibleRunner package.

        :param params: any arguments AnsibleRunner.RunnerConfig would accept
        :param kwargs: any arguments AnsibleRunner.Runner would accept
        :returns: AnsibleRunner object which holds info about the Ansible
                  execution
        """

        runner_config = ansible_runner.RunnerConfig(**params)
        runner_config.prepare()
        cmd = runner_config.generate_ansible_command()

        try:
            log.debug(f"Running the Ansible runner cmd='{cmd}'")

            runner = ansible_runner.Runner(runner_config, **kwargs)
            runner.run()
        except ansible_runner.exceptions.AnsibleRunnerException as e:
            raise ExecutionError(e)

        if runner.status != "successful":

            # Ansible runner 1.4.6-X does not expose the stderr property, so we
            # need to fallback to stdout instead
            # TODO: We'll be able to drop this code once ansible-runner 2.0 is
            # widely available
            if getattr(runner, "stderr", None) is not None:
                error = runner.stderr.read()
            else:
                error = runner.stdout.read()
            raise ExecutionError(
                f"Failed to execute Ansible command '{cmd}': {error}"
            )

        return runner

    def run_playbook(self, playbook_path, limit=None, extravars=None):
        """
        :param playbook_path: absolute path to the playbook to run as Path()
        :param limit: list of hosts to restrict the playbook execution to
        :param extravars: dictionary of extravars to pass to Ansible
        :returns: None
        """

        playbook_path_str = playbook_path.as_posix()

        params = self._get_default_params()
        params["playbook"] = playbook_path_str

        if limit:
            params["limit"] = ','.join(limit)

        if extravars:
            params["extravars"] = extravars

        self._run(params)
