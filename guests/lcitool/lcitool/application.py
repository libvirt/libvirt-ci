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

from pathlib import Path
from pkg_resources import resource_filename

from lcitool import util
from lcitool.config import Config, ConfigError
from lcitool.inventory import Inventory, InventoryError
from lcitool.projects import Projects, ProjectError
from lcitool.formatters import DockerfileFormatter, VariablesFormatter, FormatterError
from lcitool.singleton import Singleton
from lcitool.manifest import Manifest

log = logging.getLogger(__name__)


class ApplicationError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"Application error: {self.message}"


class Application(metaclass=Singleton):
    def __init__(self):
        # make sure the lcitool cache dir exists
        cache_dir_path = util.get_cache_dir()
        cache_dir_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _entrypoint_debug(args):
        cli_args = {}
        for arg, val in vars(args).items():
            if arg not in ['func', 'debug']:
                cli_args[arg] = val
        log.debug(f"Cmdline args={cli_args}")

    def _execute_playbook(self, playbook, hosts, projects, git_revision):
        log.debug(f"Executing playbook '{playbook}': hosts={hosts} "
                  f"projects={projects} gitrev={git_revision}")

        base = resource_filename(__name__, "ansible")
        config = Config()
        inventory = Inventory()

        hosts_expanded = inventory.expand_pattern(hosts)
        ansible_hosts = ",".join(hosts_expanded)
        selected_projects = Projects().expand_pattern(projects)

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

        ansible_cfg_path = Path(base, "ansible.cfg").as_posix()
        playbook_base = Path(base, "playbooks", playbook).as_posix()
        playbook_path = Path(playbook_base, "main.yml").as_posix()
        extra_vars_path = Path(util.get_temp_dir(), "extra_vars.json").as_posix()

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
            raise ApplicationError(
                f"Failed to run {playbook} on '{hosts}': {ex}"
            )

    def _action_hosts(self, args):
        self._entrypoint_debug(args)

        hosts_expanded = Inventory().expand_pattern("all")
        for host in sorted(hosts_expanded):
            print(host)

    def _action_projects(self, args):
        self._entrypoint_debug(args)

        projects_expanded = Projects().expand_pattern("all")
        for project in sorted(projects_expanded):
            print(project)

    def _action_install(self, args):
        self._entrypoint_debug(args)

        config = Config()
        inventory = Inventory()

        hosts_expanded = inventory.expand_pattern(args.hosts)
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
                raise ApplicationError(
                    f"Host {host} doesn't support installation"
                )

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

            initrd_inject = Path(util.get_temp_dir(), install_config).as_posix()

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
                raise ApplicationError(f"Failed to install '{host}': {ex}")

    def _action_update(self, args):
        self._entrypoint_debug(args)

        self._execute_playbook("update", args.hosts, args.projects,
                               args.git_revision)

    def _action_build(self, args):
        self._entrypoint_debug(args)

        # we don't keep a dependencies tree for projects, hence pattern
        # expansion would break the 'build' playbook
        for project in args.projects.split(","):
            if project == "all" or "*" in project:
                raise ApplicationError(
                    "'build' command doesn't support specifying projects by "
                    "either wildcards or the 'all' keyword"
                )

        self._execute_playbook("build", args.hosts, args.projects,
                               args.git_revision)

    def _action_variables(self, args):
        self._entrypoint_debug(args)

        hosts_expanded = Inventory().expand_pattern(args.hosts)
        projects_expanded = Projects().expand_pattern(args.projects)

        variables = VariablesFormatter().format(hosts_expanded,
                                                projects_expanded,
                                                None)

        cliargv = [args.action]
        if args.cross_arch:
            cliargv.extend(["--cross", args.cross_arch])
        cliargv.extend([args.hosts, args.projects])
        header = util.generate_file_header(cliargv)

        print(header + variables)

    def _action_dockerfile(self, args):
        self._entrypoint_debug(args)

        hosts_expanded = Inventory().expand_pattern(args.hosts)
        projects_expanded = Projects().expand_pattern(args.projects)

        dockerfile = DockerfileFormatter().format(hosts_expanded,
                                                  projects_expanded,
                                                  args.cross_arch)

        cliargv = [args.action]
        if args.cross_arch:
            cliargv.extend(["--cross", args.cross_arch])
        cliargv.extend([args.hosts, args.projects])
        header = util.generate_file_header(cliargv)

        print(header + dockerfile)

    def _action_manifest(self, args):
        manifest = Manifest(args.manifest)
        manifest.generate(args.dry_run)

    def run(self, args):
        try:
            args.func(self, args)
        except (ApplicationError,
                ConfigError,
                InventoryError,
                ProjectError,
                FormatterError) as ex:
            print(ex, file=sys.stderr)
            sys.exit(1)
