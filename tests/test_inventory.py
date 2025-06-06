# test_inventory: test lcitool Ansible inventory
#
# Copyright (C) 2022 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest
import test_utils.utils as test_utils

from pathlib import Path

from lcitool.config import Config
from lcitool.inventory import Inventory, InventoryError
from lcitool.targets import BuildTarget


pytestmark = pytest.mark.filterwarnings("ignore:'pipes' is deprecated:DeprecationWarning")


@pytest.fixture(scope="module")
def inventory(targets):
    config_path = Path(test_utils.test_data_indir(__file__), "config.yml")
    inventory_path = Path(test_utils.test_data_indir(__file__), "inventory")
    return Inventory(targets,
                     Config(path=config_path),
                     inventory_path=inventory_path)


@pytest.mark.parametrize("host,target,fully_managed", [
    pytest.param("centos-stream-9-1", "centos-stream-9", False, id="centos-stream-9-1"),
    pytest.param("192.168.1.30", "debian-12", False, id="debian-12"),
    pytest.param("fedora-test-2", "fedora-41", True, id="fedora-test-2"),
])
def test_host_facts(inventory, targets, host, target, fully_managed):
    host_facts = inventory.host_facts[host]
    assert host_facts["target"] == target
    for key, value in targets.target_facts[target].items():
        assert host_facts[key] == value
    assert host_facts.get("fully_managed", False) == fully_managed


def test_expand_hosts(inventory):
    assert sorted(inventory.expand_hosts("*centos*")) == [
        "centos-stream-9-1",
        "centos-stream-9-2",
        "some-other-centos-stream-9"
    ]
    with pytest.raises(InventoryError):
        inventory.expand_hosts("debian-12")


def test_host_target_name(inventory):
    assert inventory.get_host_target_name("fedora-test-1") == "fedora-41"


def test_group_vars(inventory, targets, packages, projects):
    target = BuildTarget(targets, packages, "fedora-41")
    group_vars = inventory.get_group_vars(target, projects, ["libvirt"])
    assert "nano" in group_vars["unwanted_packages"]
    assert "python3-libselinux" in group_vars["early_install_packages"]

    for key, value in target.facts.items():
        assert group_vars[key] == value
