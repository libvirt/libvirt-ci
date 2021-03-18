# application.py - module containing the lcitool application code
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import json
import os
import subprocess
import tempfile

from pathlib import Path
from pkg_resources import resource_filename

from lcitool import util
from lcitool.config import Config
from lcitool.inventory import Inventory
from lcitool.projects import Projects
from lcitool.formatters import DockerfileFormatter, VariablesFormatter


class Application:

    def __init__(self):
        self._config = Config()
        self._inventory = Inventory()
        self._projects = Projects()

        self._native_arch = util.get_native_arch()

    def _execute_playbook(self, playbook, hosts, projects, git_revision):
        base = resource_filename(__name__, "ansible")
        config = self._config

        config.validate_vm_settings()

        ansible_hosts = ",".join(self._inventory.expand_pattern(hosts))
        selected_projects = self._projects.expand_pattern(projects)

        if git_revision is not None:
            tokens = git_revision.split("/")
            if len(tokens) < 2:
                raise Exception(
                    "Missing or invalid git revision '{}'".format(git_revision)
                )
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

        try:
            subprocess.check_call(cmd)
        except Exception as ex:
            raise Exception(
                "Failed to run {} on '{}': {}".format(playbook, hosts, ex))
        finally:
            tempdir.cleanup()

    def _action_hosts(self, args):
        for host in self._inventory.expand_pattern("all"):
            print(host)

    def _action_projects(self, args):
        for project in self._projects.expand_pattern("all"):
            print(project)

    def _action_install(self, args):
        config = self._config

        config.validate_vm_settings()

        for host in self._inventory.expand_pattern(args.hosts):
            facts = self._inventory.get_facts(host)

            # Both memory size and disk size are stored as GiB in the
            # inventory, but virt-install expects the disk size in GiB
            # and the memory size in *MiB*, so perform conversion here
            memory_arg = str(config.values["install"]["memory_size"] * 1024)

            vcpus_arg = str(config.values["install"]["vcpus"])

            disk_arg = "size={},pool={},bus=virtio".format(
                config.values["install"]["disk_size"],
                config.values["install"]["storage_pool"],
            )
            network_arg = "network={},model=virtio".format(
                config.values["install"]["network"],
            )

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
                raise Exception(
                    "Host {} doesn't support installation".format(host)
                )

            # Unattended install scripts are being generated on the fly, based
            # on the templates present in lcitool/configs/
            unattended_options = {
                "install.url": facts["install"]["url"],
            }

            filename = resource_filename(__name__,
                                         "configs/install/{}".format(install_config))
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
            extra_arg = "console=ttyS0 inst.ks=file:/{} install={}".format(
                install_config,
                facts["install"]["url"],
            )

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

            try:
                subprocess.check_call(cmd)
            except Exception as ex:
                raise Exception("Failed to install '{}': {}".format(host, ex))
            finally:
                tempdir.cleanup()

    def _action_update(self, args):
        self._execute_playbook("update", args.hosts, args.projects,
                               args.git_revision)

    def _action_build(self, args):
        self._execute_playbook("build", args.hosts, args.projects,
                               args.git_revision)

    def _action_variables(self, args):
        print(VariablesFormatter(self._projects, self._inventory).format(args))

    def _action_dockerfile(self, args):
        print(DockerfileFormatter(self._projects,
                                  self._inventory).format(args))

    def run(self, args):
        args.func(self, args)
