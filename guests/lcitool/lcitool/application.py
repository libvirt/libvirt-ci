# application.py - module containing the lcitool application code
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import json
import logging
import os
import subprocess
import sys
import tempfile

from pathlib import Path
from pkg_resources import resource_filename

from lcitool import util
from lcitool.config import Config
from lcitool.inventory import Inventory
from lcitool.projects import Projects
from lcitool.formatters import DockerfileFormatter, VariablesFormatter
from lcitool.singleton import Singleton

log = logging.getLogger(__name__)


class Application(metaclass=Singleton):

    @staticmethod
    def _entrypoint_debug(args):
        cli_args = {}
        for arg, val in vars(args).items():
            if arg not in ['func', 'debug']:
                cli_args[arg] = val
        log.debug(f"Cmdline args={cli_args}")

    @staticmethod
    def _expand_pattern(obj, pattern):
        """
        Helper to expand fn pattern on objects that implement expansion.

        The helper exists solely to avoid the need to wrap all expand_pattern
        calls with a try-except block all around the code individually.

        :param obj: instance of a class that implements .expand_pattern()
        :return: list of items that match @pattern
        """

        try:
            return obj.expand_pattern(pattern)
        except Exception as ex:
            print(f"Failed to expand '{pattern}': {ex}", file=sys.stderr)
            sys.exit(1)

    def _execute_playbook(self, playbook, hosts, projects, git_revision):
        log.debug(f"Executing playbook '{playbook}': hosts={hosts} "
                  f"projects={projects} gitrev={git_revision}")

        base = resource_filename(__name__, "ansible")
        config = Config()
        inventory = Inventory()

        try:
            config.validate_vm_settings()
        except Exception as ex:
            print(f"Failed to validate config: {ex}", file=sys.stderr)
            sys.exit(1)

        hosts_expanded = self._expand_pattern(inventory, hosts)
        ansible_hosts = ",".join(hosts_expanded)
        selected_projects = self._expand_pattern(Projects(), projects)

        if git_revision is not None:
            tokens = git_revision.split("/")
            if len(tokens) < 2:
                print(f"Missing or invalid git revision '{git_revision}'",
                      file=sys.stderr)
                sys.exit(1)

            git_remote = tokens[0]
            git_branch = "/".join(tokens[1:])
        else:
            git_remote = "default"
            git_branch = "master"

        tempdir = tempfile.TemporaryDirectory(prefix="lcitool")

        ansible_cfg_path = Path(base, "ansible.cfg").as_posix()
        playbook_base = Path(base, "playbooks", playbook).as_posix()
        playbook_path = Path(playbook_base, "main.yml").as_posix()
        extra_vars_path = Path(tempdir.name, "extra_vars.json").as_posix()

        extra_vars = config.values
        extra_vars.update({
            "base": base,
            "playbook_base": playbook_base,
            "selected_projects": selected_projects,
            "git_remote": git_remote,
            "git_branch": git_branch,
        })

        with open(extra_vars_path, "w") as fp:
            json.dump(extra_vars, fp)

        cmd = [
            "ansible-playbook",
            "--limit", ansible_hosts,
            "--extra-vars", "@" + extra_vars_path,
        ]

        cmd.append(playbook_path)

        # We need to point Ansible to the correct configuration file,
        # and for some reason this has to be done using the environment
        # rather than through the command line
        os.environ["ANSIBLE_CONFIG"] = ansible_cfg_path

        log.debug(f"Running {cmd}")
        try:
            subprocess.check_call(cmd)
        except Exception as ex:
            print(f"Failed to run {playbook} on '{hosts}': {ex}",
                  file=sys.stderr)
            sys.exit(1)
        finally:
            tempdir.cleanup()

    def _action_hosts(self, args):
        self._entrypoint_debug(args)

        hosts_expanded = self._expand_pattern(Inventory(), "all")
        for host in sorted(hosts_expanded):
            print(host)

    def _action_projects(self, args):
        self._entrypoint_debug(args)

        projects_expanded = self._expand_pattern(Projects(), "all")
        for project in sorted(projects_expanded):
            print(project)

    def _action_install(self, args):
        self._entrypoint_debug(args)

        config = Config()
        inventory = Inventory()

        try:
            config.validate_vm_settings()
        except Exception as ex:
            print(f"Failed to validate config: {ex}", file=sys.stderr)
            sys.exit(1)

        hosts_expanded = self._expand_pattern(inventory, args.hosts)
        for host in hosts_expanded:
            facts = inventory.get_facts(host)

            # Both memory size and disk size are stored as GiB in the
            # inventory, but virt-install expects the disk size in GiB
            # and the memory size in *MiB*, so perform conversion here
            memory_arg = str(config.values["install"]["memory_size"] * 1024)

            vcpus_arg = str(config.values["install"]["vcpus"])

            conf_size = config.values["install"]["disk_size"]
            conf_pool = config.values["install"]["storage_pool"]
            disk_arg = f"size={conf_size},pool={conf_pool},bus=virtio"

            conf_network = config.values["install"]["network"]
            network_arg = f"network={conf_network},model=virtio"

            # Different operating systems require different configuration
            # files for unattended installation to work, but some operating
            # systems simply don't support unattended installation at all
            if facts["os"]["name"] in ["Debian", "Ubuntu"]:
                install_config = "preseed.cfg"
            elif facts["os"]["name"] in ["CentOS", "Fedora"]:
                install_config = "kickstart.cfg"
            elif facts["os"]["name"] == "OpenSUSE":
                install_config = "autoinst.xml"
            else:
                print(f"Host {host} doesn't support installation",
                      file=sys.stderr)
                sys.exit(1)

            try:
                unattended_options = {
                    "install.url": facts["install"]["url"],
                }
            except KeyError:
                print(f"Host {host} doesn't support installation",
                      file=sys.stderr)
                sys.exit(1)

            # Unattended install scripts are being generated on the fly, based
            # on the templates present in lcitool/configs/
            filename = resource_filename(__name__,
                                         f"configs/install/{install_config}")
            with open(filename, "r") as template:
                content = template.read()
                for option in unattended_options:
                    content = content.replace(
                        "{{ " + option + " }}",
                        unattended_options[option],
                    )

            tempdir = tempfile.TemporaryDirectory(prefix="lcitool")
            initrd_inject = Path(tempdir.name, install_config).as_posix()

            with open(initrd_inject, "w") as inject:
                inject.write(content)

            # preseed files must use a well-known name to be picked up by
            # d-i; for kickstart files, we can use whatever name we please
            # but we need to point anaconda in the right direction through
            # the 'inst.ks' kernel parameter. We can use 'inst.ks'
            # unconditionally for simplicity's sake, because distributions that
            # don't use kickstart for unattended installation will simply
            # ignore it. We do the same with the 'install' argument in order
            # to workaround a bug which causes old virt-install versions to not
            # pass the URL correctly when installing openSUSE guests
            conf_url = facts["install"]["url"]
            ks = install_config
            extra_arg = f"console=ttyS0 inst.ks=file:/{ks} install={conf_url}"

            cmd = [
                "virt-install",
                "--name", host,
                "--location", facts["install"]["url"],
                "--virt-type", config.values["install"]["virt_type"],
                "--arch", config.values["install"]["arch"],
                "--machine", config.values["install"]["machine"],
                "--cpu", config.values["install"]["cpu_model"],
                "--vcpus", vcpus_arg,
                "--memory", memory_arg,
                "--disk", disk_arg,
                "--network", network_arg,
                "--graphics", "none",
                "--console", "pty",
                "--sound", "none",
                "--rng", "device=/dev/urandom,model=virtio",
                "--initrd-inject", initrd_inject,
                "--extra-args", extra_arg,
            ]

            if not args.wait:
                cmd.append("--noautoconsole")

            log.debug(f"Running {cmd}")
            try:
                subprocess.check_call(cmd)
            except Exception as ex:
                print(f"Failed to install '{host}': {ex}", file=sys.stderr)
                sys.exit(1)
            finally:
                tempdir.cleanup()

    def _action_update(self, args):
        self._entrypoint_debug(args)

        self._execute_playbook("update", args.hosts, args.projects,
                               args.git_revision)

    def _action_build(self, args):
        self._entrypoint_debug(args)

        self._execute_playbook("build", args.hosts, args.projects,
                               args.git_revision)

    def _action_variables(self, args):
        self._entrypoint_debug(args)

        hosts_expanded = self._expand_pattern(Inventory(), args.hosts)
        projects_expanded = self._expand_pattern(Projects(), args.projects)

        try:
            variables = VariablesFormatter().format(hosts_expanded,
                                                    projects_expanded,
                                                    None)
        except Exception as ex:
            print(f"Failed to format variables: {ex}", file=sys.stderr)
            sys.exit(1)

        header = util.generate_file_header(args.action,
                                           args.hosts,
                                           args.projects,
                                           args.cross_arch)
        print(header + variables)

    def _action_dockerfile(self, args):
        self._entrypoint_debug(args)

        hosts_expanded = self._expand_pattern(Inventory(), args.hosts)
        projects_expanded = self._expand_pattern(Projects(), args.projects)

        try:
            dockerfile = DockerfileFormatter().format(hosts_expanded,
                                                      projects_expanded,
                                                      args.cross_arch)
        except Exception as ex:
            print(f"Failed to format Dockerfile: {ex}", file=sys.stderr)
            sys.exit(1)

        header = util.generate_file_header(args.action,
                                           args.hosts,
                                           args.projects,
                                           args.cross_arch)
        print(header + dockerfile)

    def run(self, args):
        args.func(self, args)
