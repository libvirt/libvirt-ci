# test_targets: test lcitool target facts
#
# Copyright (C) 2022 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

from conftest import ALL_TARGETS


@pytest.mark.parametrize("target", ALL_TARGETS)
def test_group_vars(targets, target):
    """Check selected group_vars fields for correctness."""

    facts = targets.target_facts[target]
    split = target.split('-', maxsplit=1)
    target_os = split[0]
    target_version = split[1].replace("-", "")
    target_osname_map = {
        "almalinux": "AlmaLinux",
        "alpine": "Alpine",
        "centos": "CentOS",
        "debian": "Debian",
        "fedora": "Fedora",
        "freebsd": "FreeBSD",
        "macos": "MacOS",
        "opensuse": "OpenSUSE",
        "ubuntu": "Ubuntu",
    }

    assert facts["target"] == target
    assert facts["os"]["name"] == target_osname_map[target_os]
    assert facts["os"]["version"] == target_version.capitalize()
