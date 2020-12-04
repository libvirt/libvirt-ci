# util.py - module hosting utility functions for lcitool
#
# Copyright (C) 2017-2020 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import fnmatch
import platform
import git

from pathlib import Path
from pkg_resources import resource_filename


def git_commit():
    try:
        lci_dir = Path(__file__).resolve().parent
        repo = git.Repo(lci_dir, search_parent_directories=True)
        return repo.head.object.hexsha
    except git.InvalidGitRepositoryError as ex:
        return None

def expand_pattern(pattern, source, name):
    if pattern is None:
        raise Exception("Missing {} list".format(name))

    if pattern == "all":
        pattern = "*"

    # This works correctly for single items as well as more complex
    # cases such as explicit lists, glob patterns and any combination
    # of the above
    matches = []
    for partial_pattern in pattern.split(","):

        partial_matches = []
        for item in source:
            if fnmatch.fnmatch(item, partial_pattern):
                partial_matches.append(item)

        if not partial_matches:
            raise Exception("Invalid {} list '{}'".format(name, pattern))

        matches.extend(partial_matches)

    return sorted(set(matches))


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
        raise Exception("Unsupported architecture {}".format(native_arch))
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
        raise Exception("Unsupported architecture {}".format(native_arch))
    return archmap[native_arch]


def get_openvz_repo():
    repofile_res = "ansible/playbooks/update/templates/openvz.repo.j2"
    repofile = resource_filename(__name__, repofile_res)

    with open(repofile, "r") as r:
        return r.read().rstrip()


def get_openvz_key():
    keyfile_res = "ansible/playbooks/update/templates/openvz.key"
    keyfile = resource_filename(__name__, keyfile_res)

    with open(keyfile, "r") as r:
        return r.read().rstrip()
