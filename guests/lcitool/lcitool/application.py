# application.py - module containing the lcitool application code
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import json
import os
import subprocess
import distutils.spawn
import tempfile
from pathlib import Path

import lcitool.util as Util
from lcitool.config import Config
from lcitool.inventory import Inventory
from lcitool.projects import Projects
from lcitool.formatters import DockerfileFormatter, VariablesFormatter


class Application:

    def __init__(self):
        self._config = Config()
        self._inventory = Inventory()
        self._projects = Projects()

        self._native_arch = Util.get_native_arch()

    def _execute_playbook(self, playbook, hosts, projects, git_revision):
        base = Path(Util.get_base(), "ansible").as_posix()
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

        ansible_playbook = distutils.spawn.find_executable("ansible-playbook")
        if ansible_playbook is None:
            raise Exception("Cannot find ansible-playbook in $PATH")

        cmd = [
            ansible_playbook,
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
        base = Util.get_base()
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
            # on the templates present in guests/configs/
            unattended_options = {
                "install.url": facts["install"]["url"],
            }

            with open(Path(base, "configs", install_config), 'r') as template:
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
            # the 'ks' kernel parameter. We can use 'ks' unconditionally
            # for simplicity's sake, because distributions that don't use
            # kickstart for unattended installation will simply ignore it.
            # We do the same with the 'install' argument in order to
            # workaround a bug which causes old virt-install versions to
            # not pass the URL correctly when installing openSUSE guests
            extra_arg = "console=ttyS0 ks=file:/{} install={}".format(
                install_config,
                facts["install"]["url"],
            )

            virt_install = distutils.spawn.find_executable("virt-install")
            if virt_install is None:
                raise Exception("Cannot find virt-install in $PATH")

            cmd = [
                virt_install,
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

    def _generator_build_varmap(self,
                                facts,
                                mappings,
                                pypi_mappings,
                                cpan_mappings,
                                projects,
                                cross_arch):
        pkgs = {}
        cross_pkgs = {}
        pypi_pkgs = {}
        cpan_pkgs = {}
        base_keys = [
            "default",
            facts["packaging"]["format"],
            facts["os"]["name"],
            facts["os"]["name"] + facts["os"]["version"],
        ]
        cross_keys = []
        cross_policy_keys = []
        if cross_arch:
            keys = base_keys
            if facts["packaging"]["format"] == "deb":
                # For Debian-based distros, the name of the foreign package
                # is usually the same as the native package, but there might
                # be architecture-specific overrides, so we have to look both
                # at the neutral keys and at the specific ones
                cross_keys = base_keys + [cross_arch + "-" + k for k in base_keys]
            elif facts["packaging"]["format"] == "rpm":
                # For RPM-based distros, the name of the foreign package is
                # usually very different from the native one, so we should
                # only look at the keys that are specific to cross-building
                # because otherwise we'd also pick up a bunch of native
                # packages we don't actually need
                cross_keys = [cross_arch + "-" + k for k in base_keys]
            cross_policy_keys = ["cross-policy-" + k for k in base_keys]
        else:
            keys = base_keys + [self._native_arch + "-" + k for k in base_keys]

        # We need to add the base project manually here: the standard
        # machinery hides it because it's an implementation detail
        for project in projects + ["base"]:
            for package in self._projects.get_packages(project):
                cross_policy = "native"

                if (package not in mappings and
                    package not in pypi_mappings and
                    package not in cpan_mappings):
                    raise Exception(
                        "No mapping defined for {}".format(package)
                    )

                if package in mappings:
                    for key in cross_policy_keys:
                        if key in mappings[package]:
                            cross_policy = mappings[package][key]

                    if cross_policy not in ["native", "foreign", "skip"]:
                        raise Exception(
                            "Unexpected cross arch policy {} for {}".format
                            (cross_policy, package))

                    if cross_arch and cross_policy == "foreign":
                        for key in cross_keys:
                            if key in mappings[package]:
                                pkgs[package] = mappings[package][key]
                    else:
                        for key in keys:
                            if key in mappings[package]:
                                pkgs[package] = mappings[package][key]

                if package in pypi_mappings:
                    if "default" in pypi_mappings[package]:
                        pypi_pkgs[package] = pypi_mappings[package]["default"]

                if package in cpan_mappings:
                    if "default" in cpan_mappings[package]:
                        cpan_pkgs[package] = cpan_mappings[package]["default"]

                if package in pkgs and pkgs[package] is None:
                    del pkgs[package]
                if package in pypi_pkgs and pypi_pkgs[package] is None:
                    del pypi_pkgs[package]
                if package in cpan_pkgs and cpan_pkgs[package] is None:
                    del cpan_pkgs[package]
                if package in pypi_pkgs and package in pkgs:
                    del pypi_pkgs[package]
                if package in cpan_pkgs and package in pkgs:
                    del cpan_pkgs[package]

                if (package not in pkgs and
                    package not in pypi_pkgs and
                    package not in cpan_pkgs):
                    continue

                if package in pkgs and cross_policy == "foreign":
                    cross_pkgs[package] = pkgs[package]
                if package in pkgs and cross_policy in ["skip", "foreign"]:
                    del pkgs[package]

        varmap = {
            "packaging_command": facts["packaging"]["command"],
            "paths_cc": facts["paths"]["cc"],
            "paths_ccache": facts["paths"]["ccache"],
            "paths_make": facts["paths"]["make"],
            "paths_ninja": facts["paths"]["ninja"],
            "paths_python": facts["paths"]["python"],
            "paths_pip3": facts["paths"]["pip3"],
        }

        varmap["pkgs"] = sorted(set(pkgs.values()))

        if cross_arch:
            varmap["cross_arch"] = cross_arch
            varmap["cross_abi"] = Util.native_arch_to_abi(cross_arch)

            if facts["packaging"]["format"] == "deb":
                # For Debian-based distros, the name of the foreign package
                # is obtained by appending the foreign architecture (in
                # Debian format) to the name of the native package
                cross_arch_deb = Util.native_arch_to_deb_arch(cross_arch)
                cross_pkgs = [p + ":" + cross_arch_deb for p in set(cross_pkgs.values())]
                cross_pkgs.append("gcc-" + varmap["cross_abi"])
                varmap["cross_arch_deb"] = cross_arch_deb
                varmap["cross_pkgs"] = sorted(cross_pkgs)
            elif facts["packaging"]["format"] == "rpm":
                # For RPM-based distros, all mappings have already been
                # resolved and we just need to add the cross-compiler
                cross_pkgs["gcc"] = cross_arch + "-gcc"
                varmap["cross_pkgs"] = sorted(set(cross_pkgs.values()))

        if pypi_pkgs:
            varmap["pypi_pkgs"] = sorted(set(pypi_pkgs.values()))
        if cpan_pkgs:
            varmap["cpan_pkgs"] = sorted(set(cpan_pkgs.values()))

        return varmap

    def _generator_prepare(self, name, args):
        mappings = self._projects.get_mappings()
        pypi_mappings = self._projects.get_pypi_mappings()
        cpan_mappings = self._projects.get_cpan_mappings()

        hosts = self._inventory.expand_pattern(args.hosts)
        if len(hosts) > 1:
            raise Exception(
                "Can't use '{}' use generator on multiple hosts".format(name)
            )
        host = hosts[0]

        facts = self._inventory.get_facts(host)
        cross_arch = args.cross_arch

        # We can only generate Dockerfiles for Linux
        if (name == "dockerfile" and
            facts["packaging"]["format"] not in ["deb", "rpm"]):
            raise Exception(
                "Host {} doesn't support '{}' generator".format(host, name)
            )
        if cross_arch:
            if facts["os"]["name"] not in ["Debian", "Fedora"]:
                raise Exception("Cannot cross compile on {}".format(
                    facts["os"]["name"],
                ))
            if facts["os"]["name"] == "Debian" and cross_arch.startswith("mingw"):
                raise Exception(
                    "Cannot cross compile for {} on {}".format(
                        cross_arch,
                        facts["os"]["name"],
                    )
                )
            if facts["os"]["name"] == "Fedora" and not cross_arch.startswith("mingw"):
                raise Exception(
                    "Cannot cross compile for {} on {}".format(
                        cross_arch,
                        facts["os"]["name"],
                    )
                )
            if cross_arch == self._native_arch:
                raise Exception("Cross arch {} should differ from native {}".
                                format(cross_arch, self._native_arch))

        projects = self._projects.expand_pattern(args.projects)
        for project in projects:
            if project.rfind("+mingw") >= 0:
                raise Exception("Obsolete syntax, please use --cross-arch")

        varmap = self._generator_build_varmap(facts,
                                              mappings,
                                              pypi_mappings,
                                              cpan_mappings,
                                              projects,
                                              cross_arch)
        return facts, cross_arch, varmap

    def _action_variables(self, args):
        facts, cross_arch, varmap = self._generator_prepare("variables", args)
        VariablesFormatter().format(varmap)

    def _action_dockerfile(self, args):
        facts, cross_arch, varmap = self._generator_prepare("dockerfile", args)
        DockerfileFormatter().format(facts, cross_arch, varmap)

    def run(self, args):
        args.func(self, args)
