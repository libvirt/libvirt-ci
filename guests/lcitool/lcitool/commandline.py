# commandline.py - module containing the lcitool command line parser
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse

from lcitool.application import Application


class CommandLine:

    def __init__(self):
        # Common option parsers to inherit from
        hostopt = argparse.ArgumentParser(add_help=False)
        hostopt.add_argument(
            "host",
            help="host to act on",
        )

        hostsopt = argparse.ArgumentParser(add_help=False)
        hostsopt.add_argument(
            "hosts",
            help="list of hosts to act on (accepts globs)",
        )

        targetopt = argparse.ArgumentParser(add_help=False)
        targetopt.add_argument(
            "target",
            help="target to operate on",
        )

        projectsopt = argparse.ArgumentParser(add_help=False)
        projectsopt.add_argument(
            "projects",
            help="list of projects to consider (accepts globs)",
        )

        gitrevopt = argparse.ArgumentParser(add_help=False)
        gitrevopt.add_argument(
            "-g", "--git-revision",
            help="git revision to build (remote/branch)",
        )

        containerizedopt = argparse.ArgumentParser(add_help=False)
        containerizedopt.add_argument(
            "-c", "--containerized",
            default=False,
            action="store_true",
            help="only report hosts supporting containers")

        crossarchopt = argparse.ArgumentParser(add_help=False)
        crossarchopt.add_argument(
            "-x", "--cross-arch",
            help="target architecture for cross compiler",
        )

        waitopt = argparse.ArgumentParser(add_help=False)
        waitopt.add_argument(
            "-w", "--wait",
            help="wait for installation to complete",
            default=False,
            action="store_true",
        )

        manifestopt = argparse.ArgumentParser(add_help=False)
        manifestopt.add_argument(
            "manifest",
            metavar="PATH",
            type=argparse.FileType('r'),
            help="path to CI manifest file",
        )

        dryrunopt = argparse.ArgumentParser(add_help=False)
        dryrunopt.add_argument(
            "-n", "--dry-run",
            action="store_true",
            help="print what files would be generated",
        )

        # Main parser
        self._parser = argparse.ArgumentParser(
            conflict_handler="resolve",
            description="libvirt CI guest management tool",
        )

        self._parser.add_argument(
            "--debug",
            help="display debugging information",
            action="store_true",
        )

        subparsers = self._parser.add_subparsers(metavar="ACTION",
                                                 dest="action")
        subparsers.required = True

        # lcitool subcommand parsers
        installparser = subparsers.add_parser(
            "install",
            help="perform unattended host installation",
            parents=[hostopt, waitopt],
        )
        installparser.set_defaults(func=Application._action_install)

        updateparser = subparsers.add_parser(
            "update",
            help="prepare hosts and keep them updated",
            parents=[hostsopt, projectsopt, gitrevopt],
        )
        updateparser.set_defaults(func=Application._action_update)

        buildparser = subparsers.add_parser(
            "build",
            help="build projects on hosts",
            parents=[hostsopt, gitrevopt],
        )
        buildparser.add_argument(
            "projects",
            help="list of projects to consider (does NOT accept globs)",
        )
        buildparser.set_defaults(func=Application._action_build)

        hostsparser = subparsers.add_parser(
            "hosts",
            help="list all known hosts",
        )
        hostsparser.set_defaults(func=Application._action_hosts)

        targetsparser = subparsers.add_parser(
            "targets",
            help="list all supported target OS platforms",
            parents=[containerizedopt],
        )
        targetsparser.set_defaults(func=Application._action_targets)

        projectsparser = subparsers.add_parser(
            "projects",
            help="list all known projects",
        )
        projectsparser.set_defaults(func=Application._action_projects)

        variablesparser = subparsers.add_parser(
            "variables",
            help="generate variables",
            parents=[targetopt, projectsopt, crossarchopt],
        )
        variablesparser.set_defaults(func=Application._action_variables)

        dockerfileparser = subparsers.add_parser(
            "dockerfile",
            help="generate Dockerfile",
            parents=[targetopt, projectsopt, crossarchopt],
        )
        dockerfileparser.set_defaults(func=Application._action_dockerfile)

        manifestparser = subparsers.add_parser(
            "manifest",
            help="apply the CI manifest (doesn't access the host)",
            parents=[manifestopt, dryrunopt])
        manifestparser.set_defaults(func=Application._action_manifest)

    def parse(self):
        return self._parser.parse_args()
