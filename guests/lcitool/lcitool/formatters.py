# formatters.py - module containing various recipe formatting backends
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import abc
import sys
import textwrap
from pathlib import Path

import lcitool.util as Util


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
        base = Util.get_base()
        cross_name = "{}.meson".format(cross_abi)
        with open(Path(base, "cross", cross_name), "r") as c:
            return c.read().rstrip()


class DockerfileFormatter(Formatter):
    def __init__(self, projects, inventory):
        self._native_arch = Util.get_native_arch()
        self._projects = projects
        self._inventory = inventory

    def format(self, facts, cross_arch, varmap):
        pkg_align = " \\\n" + (" " * len("RUN " + facts["packaging"]["command"] + " "))
        pypi_pkg_align = " \\\n" + (" " * len("RUN pip3 "))
        cpan_pkg_align = " \\\n" + (" " * len("RUN cpanm "))

        varmap["pkgs"] = pkg_align[1:] + pkg_align.join(varmap["pkgs"])

        if "cross_pkgs" in varmap:
            varmap["cross_pkgs"] = pkg_align[1:] + pkg_align.join(varmap["cross_pkgs"])
        if "pypi_pkgs" in varmap:
            varmap["pypi_pkgs"] = pypi_pkg_align[1:] + pypi_pkg_align.join(varmap["pypi_pkgs"])
        if "cpan_pkgs" in varmap:
            varmap["cpan_pkgs"] = cpan_pkg_align[1:] + cpan_pkg_align.join(varmap["cpan_pkgs"])

        print("FROM {}".format(facts["docker"]["base"]))

        commands = []

        if facts["packaging"]["format"] == "deb":
            commands.extend([
                "export DEBIAN_FRONTEND=noninteractive",
                "{packaging_command} update",
                "{packaging_command} dist-upgrade -y",
                "{packaging_command} install --no-install-recommends -y {pkgs}",
                "{packaging_command} autoremove -y",
                "{packaging_command} autoclean -y",
                "sed -Ei 's,^# (en_US\\.UTF-8 .*)$,\\1,' /etc/locale.gen",
                "dpkg-reconfigure locales",
            ])
        elif facts["packaging"]["format"] == "rpm":
            # Rawhide needs this because the keys used to sign packages are
            # cycled from time to time
            if facts["os"]["name"] == "Fedora" and facts["os"]["version"] == "Rawhide":
                commands.extend([
                    "{packaging_command} update -y --nogpgcheck fedora-gpg-keys",
                ])

            if facts["os"]["name"] == "CentOS":
                # For the Stream release we need to install the Stream
                # repositories
                if facts["os"]["version"] == "Stream":
                    commands.append(
                        "{packaging_command} install -y centos-release-stream"
                    )

                # Starting with CentOS 8, most -devel packages are shipped in
                # the PowerTools repository, which is not enabled by default
                if facts["os"]["version"] != "7":
                    powertools = "PowerTools"

                    # for the Stream release, we want the Stream-Powertools
                    # version of the repository
                    if facts["os"]["version"] == "Stream":
                        powertools = "Stream-PowerTools"

                    commands.extend([
                        "{packaging_command} install 'dnf-command(config-manager)' -y",
                        "{packaging_command} config-manager --set-enabled -y " + powertools,
                    ])

                # VZ development packages are only available for CentOS/RHEL-7
                # right now and need a 3rd party repository enabled
                if facts["os"]["version"] == "7":
                    repo = Util.get_openvz_repo()
                    varmap["vzrepo"] = "\\n\\\n".join(repo.split("\n"))
                    key = Util.get_openvz_key()
                    varmap["vzkey"] = "\\n\\\n".join(key.split("\n"))

                    commands.extend([
                        "echo -e '{vzrepo}' > /etc/yum.repos.d/openvz.repo",
                        "echo -e '{vzkey}' > /etc/pki/rpm-gpg/RPM-GPG-KEY-OpenVZ",
                        "rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-OpenVZ",
                    ])

                # Some of the packages we need are not part of CentOS proper
                # and are only available through EPEL
                commands.extend([
                    "{packaging_command} install -y epel-release",
                ])

            commands.extend([
                "{packaging_command} update -y",
                "{packaging_command} install -y {pkgs}",
            ])

            # openSUSE doesn't seem to have a convenient way to remove all
            # unnecessary packages, but CentOS and Fedora do
            if facts["os"]["name"] == "OpenSUSE":
                commands.extend([
                    "{packaging_command} clean --all",
                ])
            else:
                commands.extend([
                    "{packaging_command} autoremove -y",
                    "{packaging_command} clean all -y",
                ])

        commands.extend([
            "mkdir -p /usr/libexec/ccache-wrappers",
        ])

        if cross_arch:
            commands.extend([
                "ln -s {paths_ccache} /usr/libexec/ccache-wrappers/{cross_abi}-cc",
                "ln -s {paths_ccache} /usr/libexec/ccache-wrappers/{cross_abi}-$(basename {paths_cc})",
            ])
        else:
            commands.extend([
                "ln -s {paths_ccache} /usr/libexec/ccache-wrappers/cc",
                "ln -s {paths_ccache} /usr/libexec/ccache-wrappers/$(basename {paths_cc})",
            ])

        script = "\nRUN " + (" && \\\n    ".join(commands)) + "\n"
        sys.stdout.write(script.format(**varmap))

        if cross_arch:
            cross_commands = []

            # Intentionally a separate RUN command from the above
            # so that the common packages of all cross-built images
            # share a Docker image layer.
            if facts["packaging"]["format"] == "deb":
                cross_commands.extend([
                    "export DEBIAN_FRONTEND=noninteractive",
                    "dpkg --add-architecture {cross_arch_deb}",
                    "{packaging_command} update",
                    "{packaging_command} dist-upgrade -y",
                    "{packaging_command} install --no-install-recommends -y dpkg-dev",
                    "{packaging_command} install --no-install-recommends -y {cross_pkgs}",
                    "{packaging_command} autoremove -y",
                    "{packaging_command} autoclean -y",
                ])
            elif facts["packaging"]["format"] == "rpm":
                cross_commands.extend([
                    "{packaging_command} install -y {cross_pkgs}",
                    "{packaging_command} clean all -y",
                ])

            if not cross_arch.startswith("mingw"):
                cross_commands.extend([
                    "mkdir -p /usr/local/share/meson/cross",
                    "echo \"{cross_meson}\" > /usr/local/share/meson/cross/{cross_abi}",
                ])

                cross_meson = self._get_meson_cross(varmap["cross_abi"])
                varmap["cross_meson"] = cross_meson.replace("\n", "\\n\\\n")

            cross_script = "\nRUN " + (" && \\\n    ".join(cross_commands)) + "\n"
            sys.stdout.write(cross_script.format(**varmap))

        if "pypi_pkgs" in varmap:
            sys.stdout.write(textwrap.dedent("""
                RUN pip3 install {pypi_pkgs}
            """).format(**varmap))

        if "cpan_pkgs" in varmap:
            sys.stdout.write(textwrap.dedent("""
                RUN cpanm --notest {cpan_pkgs}
            """).format(**varmap))

        sys.stdout.write(textwrap.dedent("""
            ENV LANG "en_US.UTF-8"

            ENV MAKE "{paths_make}"
            ENV NINJA "{paths_ninja}"
            ENV PYTHON "{paths_python}"

            ENV CCACHE_WRAPPERSDIR "/usr/libexec/ccache-wrappers"
        """).format(**varmap))

        if cross_arch:
            cross_vars = [
                "ENV ABI \"{cross_abi}\"",
                "ENV CONFIGURE_OPTS \"--host={cross_abi}\"",
            ]

            if cross_arch.startswith("mingw"):
                cross_vars.append(
                    "ENV MESON_OPTS \"--cross-file=/usr/share/mingw/toolchain-{cross_arch}.meson\""
                )
            else:
                cross_vars.append(
                    "ENV MESON_OPTS \"--cross-file={cross_abi}\"",
                )

            cross_env = "\n" + "\n".join(cross_vars) + "\n"
            sys.stdout.write(cross_env.format(**varmap))


class VariablesFormatter(Formatter):
    def __init__(self, projects, inventory):
        self._native_arch = Util.get_native_arch()
        self._projects = projects
        self._inventory = inventory

    def format(self, varmap):

        for key in varmap:
            if key == "pkgs" or key.endswith("_pkgs"):
                name = key
                value = " ".join(varmap[key])
            elif key.startswith("paths_"):
                name = key[len("paths_"):]
                value = varmap[key]
            else:
                name = key
                value = varmap[key]
            print("{}='{}'".format(name.upper(), value))
