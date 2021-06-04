# util.py - module hosting utility functions for lcitool
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import fnmatch
import git
import logging
import platform
import textwrap

from pathlib import Path

log = logging.getLogger(__name__)


def git_commit():
    try:
        lci_dir = Path(__file__).resolve().parent
        repo = git.Repo(lci_dir, search_parent_directories=True)
        return repo.head.object.hexsha
    except git.InvalidGitRepositoryError:
        return None


def expand_pattern(pattern, iterable, name):
    log.debug(f"Expanding {name} pattern '{pattern}' on '{iterable}'")

    if pattern is None:
        raise Exception(f"Missing {name} list")

    if pattern == "all":
        pattern = "*"

    # This works correctly for single items as well as more complex
    # cases such as explicit lists, glob patterns and any combination
    # of the above
    matches = []
    for partial_pattern in pattern.split(","):

        partial_matches = []
        for item in iterable:
            if fnmatch.fnmatch(item, partial_pattern):
                partial_matches.append(item)

        if not partial_matches:
            raise Exception(f"Invalid {name} list '{pattern}'")

        matches.extend(partial_matches)

    return set(matches)


def get_native_arch():
    # Same canonicalization as libvirt virArchFromHost
    arch = platform.machine()
    if arch in ["i386", "i486", "i586"]:
        arch = "i686"
    if arch == "amd64":
        arch = "x86_64"
    return arch


def native_arch_to_abi(native_arch):
    archmap = {
        "aarch64": "aarch64-linux-gnu",
        "armv6l": "arm-linux-gnueabi",
        "armv7l": "arm-linux-gnueabihf",
        "i686": "i686-linux-gnu",
        "mingw32": "i686-w64-mingw32",
        "mingw64": "x86_64-w64-mingw32",
        "mips": "mips-linux-gnu",
        "mipsel": "mipsel-linux-gnu",
        "mips64el": "mips64el-linux-gnuabi64",
        "ppc64le": "powerpc64le-linux-gnu",
        "s390x": "s390x-linux-gnu",
        "x86_64": "x86_64-linux-gnu",
    }
    if native_arch not in archmap:
        raise Exception(f"Unsupported architecture {native_arch}")
    return archmap[native_arch]


def native_arch_to_deb_arch(native_arch):
    archmap = {
        "aarch64": "arm64",
        "armv6l": "armel",
        "armv7l": "armhf",
        "i686": "i386",
        "mips": "mips",
        "mipsel": "mipsel",
        "mips64el": "mips64el",
        "ppc64le": "ppc64el",
        "s390x": "s390x",
        "x86_64": "amd64",
    }
    if native_arch not in archmap:
        raise Exception(f"Unsupported architecture {native_arch}")
    return archmap[native_arch]


def generate_file_header(action, hosts, projects, cross_arch):
    cli_args = []
    if cross_arch:
        cli_args.extend(["--cross", cross_arch])
    cli_args.extend([hosts, projects])
    cli_args_formatted = " ".join(cli_args)

    commit = git_commit()
    url = "https://gitlab.com/libvirt/libvirt-ci"
    if commit is not None:
        url = url + "/-/commit/" + commit

    header = textwrap.dedent(
        f"""\
        # THIS FILE WAS AUTO-GENERATED
        #
        #  $ lcitool {action} {cli_args_formatted}
        #
        # {url}

        """
    )
    return header
