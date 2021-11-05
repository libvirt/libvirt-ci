# formatters.py - module containing various recipe formatting backends
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import abc
import json
import logging

from pkg_resources import resource_filename

from lcitool import util
from lcitool.inventory import Inventory
from lcitool.projects import Projects
from lcitool.package import package_names_by_type


log = logging.getLogger(__name__)


class FormatterError(Exception):
    """
    Global exception type for this module.

    Contains a detailed message coming from one of its subclassed exception
    types. On the application level, this is the exception type you should be
    catching instead of the subclassed types.
    """

    pass


class DockerfileError(FormatterError):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"Docker formatter error: {self.message}"


class VariablesError(FormatterError):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"Variables formatter error: {self.message}"


class Formatter(metaclass=abc.ABCMeta):
    """
    This an abstract base class that each formatter must subclass.
    """

    @abc.abstractmethod
    def format(self):
        """
        Outputs a recipe using format implemented by a Foo(Formatter) subclass

        Given the input, this method will generate and output an instruction
        recipe (or a configuration file in general) using the format of the
        subclassed formatter. Each formatter must implement this method.

        Returns a formatted recipe as string.
        """
        pass

    def _get_meson_cross(self, cross_abi):
        cross_name = resource_filename(__name__,
                                       f"cross/{cross_abi}.meson")
        with open(cross_name, "r") as c:
            return c.read().rstrip()

    def _generator_build_varmap(self,
                                facts,
                                selected_projects,
                                cross_arch):
        projects = Projects()

        # we need the 'base' internal project here, but packages for internal
        # projects are not resolved via the public API, so it requires special
        # handling
        pkgs = projects.internal_projects["base"].get_packages(facts,
                                                               cross_arch)

        # we can now load packages for the rest of the projects
        pkgs.update(projects.get_packages(selected_projects, facts, cross_arch))
        package_names = package_names_by_type(pkgs)

        varmap = {
            "packaging_command": facts["packaging"]["command"],
            "paths_ccache": facts["paths"]["ccache"],
            "paths_make": facts["paths"]["make"],
            "paths_ninja": facts["paths"]["ninja"],
            "paths_python": facts["paths"]["python"],
            "paths_pip3": facts["paths"]["pip3"],

            "cross_arch": None,
            "cross_abi": None,
            "cross_arch_deb": None,

            "mappings": [pkg.mapping for pkg in pkgs.values()],
            "pkgs": package_names["native"],
            "cross_pkgs": package_names["cross"],
            "pypi_pkgs": package_names["pypi"],
            "cpan_pkgs": package_names["cpan"],
        }

        if cross_arch:
            varmap["cross_arch"] = cross_arch
            varmap["cross_abi"] = util.native_arch_to_abi(cross_arch)

            if facts["packaging"]["format"] == "deb":
                cross_arch_deb = util.native_arch_to_deb_arch(cross_arch)
                varmap["cross_arch_deb"] = cross_arch_deb

        log.debug(f"Generated varmap: {varmap}")
        return varmap

    def _generator_prepare(self, target, selected_projects, cross_arch):
        log.debug(f"Generating varmap for "
                  f"target='{target}', "
                  f"projects='{selected_projects}', "
                  f"cross_arch='{cross_arch}'")

        name = self.__class__.__name__.lower()

        try:
            facts = Inventory().target_facts[target]
        except KeyError:
            raise FormatterError(f"Invalid target '{target}'")

        # We can only generate Dockerfiles for Linux
        if (name == "dockerfileformatter" and
            facts["packaging"]["format"] not in ["apk", "deb", "rpm"]):
            raise FormatterError(f"Target {target} doesn't support this generator")

        varmap = self._generator_build_varmap(facts,
                                              selected_projects,
                                              cross_arch)
        return facts, cross_arch, varmap


class DockerfileFormatter(Formatter):
    def _format_dockerfile(self, target, project, facts, cross_arch, varmap):
        strings = []
        pkg_align = " \\\n" + (" " * len("RUN " + facts["packaging"]["command"] + " "))
        pypi_pkg_align = " \\\n" + (" " * len("RUN pip3 "))
        cpan_pkg_align = " \\\n" + (" " * len("RUN cpanm "))

        varmap["pkgs"] = pkg_align[1:] + pkg_align.join(varmap["pkgs"])

        if varmap["cross_pkgs"]:
            varmap["cross_pkgs"] = pkg_align[1:] + pkg_align.join(varmap["cross_pkgs"])
        if varmap["pypi_pkgs"]:
            varmap["pypi_pkgs"] = pypi_pkg_align[1:] + pypi_pkg_align.join(varmap["pypi_pkgs"])
        if varmap["cpan_pkgs"]:
            varmap["cpan_pkgs"] = cpan_pkg_align[1:] + cpan_pkg_align.join(varmap["cpan_pkgs"])

        base = facts["containers"]["base"]
        strings.append(f"FROM {base}")

        commands = []
        common_commands = []

        varmap["nosync"] = ""
        if facts["packaging"]["format"] == "apk":
            # TODO: 'libeatmydata' package is present in 'testing' repo
            # for Alpine Edge. Once it graduates to 'main' repo we
            # should use it here
            # varmap["nosync"] = "eatmydata "
            # "{packaging_command} add libeatmydata",
            commands.extend([
                "{packaging_command} update",
                "{packaging_command} upgrade"])

            commands.extend([
                "{nosync}{packaging_command} add {pkgs}",
            ])
        elif facts["packaging"]["format"] == "deb":
            varmap["nosync"] = "eatmydata "
            commands.extend([
                "export DEBIAN_FRONTEND=noninteractive",
                "{packaging_command} update",
                "{packaging_command} install -y eatmydata",
                "{nosync}{packaging_command} dist-upgrade -y"])

            commands.extend([
                "{nosync}{packaging_command} install --no-install-recommends -y {pkgs}",
                "{nosync}{packaging_command} autoremove -y",
                "{nosync}{packaging_command} autoclean -y",
                "sed -Ei 's,^# (en_US\\.UTF-8 .*)$,\\1,' /etc/locale.gen",
                "dpkg-reconfigure locales",
            ])
            common_commands.extend([
                "dpkg-query --showformat '${{Package}}_${{Version}}_${{Architecture}}\\n' --show > /packages.txt"
            ])
        elif facts["packaging"]["format"] == "rpm":
            # Rawhide needs this because the keys used to sign packages are
            # cycled from time to time
            if facts["os"]["name"] == "Fedora" and facts["os"]["version"] == "Rawhide":
                commands.extend([
                    "{packaging_command} update -y --nogpgcheck fedora-gpg-keys",
                ])

            if facts["os"]["name"] == "Fedora":
                varmap["nosync"] = "nosync "
                nosyncsh = [
                    "#!/bin/sh",
                    "if test -d /usr/lib64",
                    "then",
                    "    export LD_PRELOAD=/usr/lib64/nosync/nosync.so",
                    "else",
                    "    export LD_PRELOAD=/usr/lib/nosync/nosync.so",
                    "fi",
                    "exec \"$@\""
                ]
                commands.extend([
                    "{packaging_command} install -y nosync",
                    "echo -e '%s' > /usr/bin/nosync" % "\\n\\\n".join(nosyncsh),
                    "chmod +x /usr/bin/nosync"])

            # First we need to run update, then config and install
            commands.extend(["{nosync}{packaging_command} update -y"])

            if facts["os"]["name"] == "CentOS":
                # Starting with CentOS 8, most -devel packages are shipped in
                # a separate repository which is not enabled by default. The
                # name of this repository has changed over time
                commands.extend([
                    "{nosync}{packaging_command} install 'dnf-command(config-manager)' -y",
                ])
                if facts["os"]["version"] == "Stream9":
                    commands.extend([
                        "{nosync}{packaging_command} config-manager --set-enabled -y crb",
                    ])
                if facts["os"]["version"] in ["8", "Stream8"]:
                    commands.extend([
                        "{nosync}{packaging_command} config-manager --set-enabled -y powertools",
                    ])

                # Not all of the virt related -devel packages are provided by
                # virt:rhel module so we have to enable AV repository as well.
                # CentOS Stream 9 no longer uses modules for virt
                if facts["os"]["version"] in ["8", "Stream8"]:
                    commands.extend([
                        "{nosync}{packaging_command} install -y centos-release-advanced-virtualization",
                    ])

                # Some of the packages we need are not part of CentOS proper
                # and are only available through EPEL
                # FIXME Drop check once EPEL for CentOS Stream 9 exists
                if facts["os"]["version"] != "Stream9":
                    commands.extend([
                        "{nosync}{packaging_command} install -y epel-release",
                    ])

            commands.extend(["{nosync}{packaging_command} install -y {pkgs}"])

            # openSUSE doesn't seem to have a convenient way to remove all
            # unnecessary packages, but CentOS and Fedora do
            if facts["os"]["name"] == "OpenSUSE":
                commands.extend([
                    "{nosync}{packaging_command} clean --all",
                ])
            else:
                commands.extend([
                    "{nosync}{packaging_command} autoremove -y",
                    "{nosync}{packaging_command} clean all -y",
                ])

            common_commands.extend(["rpm -qa | sort > /packages.txt"])

        if "ccache" in varmap["mappings"]:
            compilers = set()
            for compiler in ["gcc", "clang"]:
                if compiler in varmap["mappings"]:
                    compilers.add(compiler)
                    compilers.add("cc")
            for compiler in ["g++"]:
                if compiler in varmap["mappings"]:
                    compilers.add(compiler)
                    compilers.add("c++")

            if compilers:
                common_commands.extend([
                    "mkdir -p /usr/libexec/ccache-wrappers",
                ])

                for compiler in sorted(compilers):
                    if cross_arch:
                        compiler = "{cross_abi}-" + compiler
                    common_commands.extend([
                        "ln -s {paths_ccache} /usr/libexec/ccache-wrappers/" + compiler,
                    ])

        if not cross_arch:
            commands.extend(common_commands)
        script = "\nRUN " + (" && \\\n    ".join(commands))
        strings.append(script.format(**varmap))

        if cross_arch:
            cross_commands = []

            # Intentionally a separate RUN command from the above
            # so that the common packages of all cross-built images
            # share a Docker image layer.
            if facts["packaging"]["format"] == "deb":
                cross_commands.extend([
                    "export DEBIAN_FRONTEND=noninteractive",
                    "dpkg --add-architecture {cross_arch_deb}",
                ])
                if cross_arch == "riscv64":
                    cross_commands.extend([
                        "{nosync}{packaging_command} install debian-ports-archive-keyring",
                        "{nosync}echo 'deb http://ftp.ports.debian.org/debian-ports/ sid main' > /etc/apt/sources.list.d/ports.list",
                        "{nosync}echo 'deb http://ftp.ports.debian.org/debian-ports/ unreleased main' >> /etc/apt/sources.list.d/ports.list",
                    ])
                cross_commands.extend([
                    "{nosync}{packaging_command} update",
                    "{nosync}{packaging_command} dist-upgrade -y",
                    "{nosync}{packaging_command} install --no-install-recommends -y dpkg-dev",
                    "{nosync}{packaging_command} install --no-install-recommends -y {cross_pkgs}",
                    "{nosync}{packaging_command} autoremove -y",
                    "{nosync}{packaging_command} autoclean -y",
                ])
            elif facts["packaging"]["format"] == "rpm":
                cross_commands.extend([
                    "{nosync}{packaging_command} install -y {cross_pkgs}",
                    "{nosync}{packaging_command} clean all -y",
                ])

            if not cross_arch.startswith("mingw"):
                cross_commands.extend([
                    "mkdir -p /usr/local/share/meson/cross",
                    "echo \"{cross_meson}\" > /usr/local/share/meson/cross/{cross_abi}",
                ])

                cross_meson = self._get_meson_cross(varmap["cross_abi"])
                varmap["cross_meson"] = cross_meson.replace("\n", "\\n\\\n")

            cross_commands.extend(common_commands)
            cross_script = "\nRUN " + (" && \\\n    ".join(cross_commands))
            strings.append(cross_script.format(**varmap))

        if varmap["pypi_pkgs"]:
            strings.append("\nRUN pip3 install {pypi_pkgs}".format(**varmap))

        if varmap["cpan_pkgs"]:
            strings.append("\nRUN cpanm --notest {cpan_pkgs}".format(**varmap))

        common_vars = ["ENV LANG \"en_US.UTF-8\""]
        if "make" in varmap["mappings"]:
            common_vars += ["ENV MAKE \"{paths_make}\""]
        if "meson" in varmap["mappings"]:
            common_vars += ["ENV NINJA \"{paths_ninja}\""]
        if "python3" in varmap["mappings"]:
            common_vars += ["ENV PYTHON \"{paths_python}\""]
        if "ccache" in varmap["mappings"]:
            common_vars += ["ENV CCACHE_WRAPPERSDIR \"/usr/libexec/ccache-wrappers\""]

        common_env = "\n" + "\n".join(common_vars)
        strings.append(common_env.format(**varmap))

        if cross_arch:
            cross_vars = ["ENV ABI \"{cross_abi}\""]
            if "autoconf" in varmap["mappings"]:
                cross_vars.append("ENV CONFIGURE_OPTS \"--host={cross_abi}\"")

            if "meson" in varmap["mappings"]:
                if cross_arch.startswith("mingw"):
                    cross_vars.append(
                        "ENV MESON_OPTS \"--cross-file=/usr/share/mingw/toolchain-{cross_arch}.meson\""
                    )
                else:
                    cross_vars.append(
                        "ENV MESON_OPTS \"--cross-file={cross_abi}\"",
                    )

            cross_env = "\n" + "\n".join(cross_vars)
            strings.append(cross_env.format(**varmap))

        return strings

    def format(self, target, selected_projects, cross_arch):
        """
        Generates and formats a Dockerfile.

        Given the application commandline arguments, this function will take
        the projects and inventory attributes and generate a Dockerfile
        describing an environment for doing a project build on a given
        inventory platform.

        :param args: Application class' command line arguments
        :returns: String represented Dockerfile
        """

        log.debug(f"Generating Dockerfile for projects '{selected_projects}' "
                  f"on target '{target}' (cross_arch={cross_arch})")

        try:
            facts, cross_arch, varmap = self._generator_prepare(target,
                                                                selected_projects,
                                                                cross_arch)
        except FormatterError as ex:
            raise DockerfileError(str(ex))

        return '\n'.join(self._format_dockerfile(target, selected_projects,
                                                 facts, cross_arch, varmap))


class VariablesFormatter(Formatter):
    @staticmethod
    def _normalize_variables(varmap):
        normalized_vars = {}
        for key in varmap:
            if varmap[key] is None:
                continue

            if key == "mappings":
                # For internal use only
                continue

            if key.startswith("paths_"):
                name = key[len("paths_"):]
            else:
                name = key
            normalized_vars[name] = varmap[key]

        return normalized_vars

    @staticmethod
    @abc.abstractmethod
    def _format_variables(varmap):
        pass

    def format(self, target, selected_projects, cross_arch):
        """
        Generates and formats environment variables as KEY=VAL pairs.

        Given the commandline arguments, this function will take take the
        projects and inventory attributes and generate a KEY=VAL encoded list
        of environment variables that can be consumed by various CI backends.

        :param args: Application class' command line arguments
        :returns: String represented list of environment variables
        """

        log.debug(f"Generating variables for projects '{selected_projects} on "
                  f"target '{target}' (cross_arch={cross_arch})")

        try:
            _, _, varmap = self._generator_prepare(target,
                                                   selected_projects,
                                                   cross_arch)
        except FormatterError as ex:
            raise VariablesError(str(ex))

        varmap = self._normalize_variables(varmap)
        return self._format_variables(varmap)


class ShellVariablesFormatter(VariablesFormatter):
    @staticmethod
    def _format_variables(varmap):
        strings = []

        for key in sorted(varmap.keys()):
            value = varmap[key]
            if key == "pkgs" or key.endswith("_pkgs"):
                value = " ".join(varmap[key])

            uppername = key.upper()
            strings.append(f"{uppername}='{value}'")
        return "\n".join(strings)


class JSONVariablesFormatter(VariablesFormatter):
    @staticmethod
    def _format_variables(varmap):
        return json.dumps(varmap, indent="  ", sort_keys=True)
