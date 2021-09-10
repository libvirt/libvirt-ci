# test_packages: test the package mapping resolving code
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest
import yaml

from pathlib import Path
from lcitool.inventory import Inventory
from lcitool.projects import Project, Projects, ProjectError
from lcitool.package import NativePackage, CrossPackage, PyPIPackage, CPANPackage


ALL_TARGETS = sorted(Inventory().targets)


def get_non_cross_targets():
    ret = []
    for target in ALL_TARGETS:
        if target.startswith("debian-") or target.startswith("fedora-"):
            continue

        ret.append(target)
    return ret


@pytest.fixture
def data_dir():
    return Path(__file__).parent.joinpath("data")


@pytest.fixture
def facts():
    return Inventory().target_facts


@pytest.fixture
def test_project(data_dir):
    return Project("packages_in", Path(data_dir, "packages_in.yml"))


def test_verify_all_mappings_and_packages(data_dir):
    actual_packages = set(Projects().mappings["mappings"].keys())

    # load the expected results
    res_file = Path(data_dir, "packages_in.yml")
    with open(res_file) as fd:
        yaml_data = yaml.safe_load(fd)
        expected_packages = set(yaml_data["packages"])

    assert actual_packages == expected_packages


@pytest.mark.parametrize("target", ALL_TARGETS, ids=ALL_TARGETS)
def test_package_resolution(data_dir, facts, test_project, target):
    pkgs = test_project.get_packages(facts[target])

    # load the expected results
    res_file = Path(data_dir, "packages_out", f"{target}.yml")
    with open(res_file) as fd:
        expected = yaml.safe_load(fd)

    # now get the actual results
    for cls in [NativePackage, CrossPackage, PyPIPackage, CPANPackage]:
        pkg_type = cls.__name__.replace("Package", "").lower()

        actual_names = set([p.name for p in pkgs.values() if isinstance(p, cls)])
        expected_names = set(expected.get(pkg_type, []))
        assert actual_names == expected_names


@pytest.mark.parametrize(
    "target,arch",
    [
        pytest.param("debian-10", "s390x", id="debian-10-cross-s390x"),
        pytest.param("fedora-rawhide", "mingw64", id="fedora-rawhide-cross-mingw64")
    ],
)
def test_cross_package_resolution(data_dir, facts, test_project, target, arch):
    pkgs = test_project.get_packages(facts[target], cross_arch=arch)

    # load the expected results
    res_file = Path(data_dir, "packages_out", f"{target}-cross-{arch}.yml")
    with open(res_file) as fd:
        expected = yaml.safe_load(fd)

    # now get the actual results
    for cls in [NativePackage, CrossPackage, PyPIPackage, CPANPackage]:
        pkg_type = cls.__name__.replace("Package", "").lower()

        actual_names = set([p.name for p in pkgs.values() if isinstance(p, cls)])
        expected_names = set(expected.get(pkg_type, []))
        assert actual_names == expected_names


@pytest.mark.parametrize(
    "target",
    [pytest.param(target, id=target) for target in get_non_cross_targets()],
)
def test_unsuppported_cross_platform(facts, test_project, target):
    with pytest.raises(ProjectError):
        test_project.get_packages(facts[target], cross_arch="s390x")


@pytest.mark.parametrize(
    "target,arch",
    [
        pytest.param("debian-sid", "mingw64", id="debian-sid-cross-mingw64"),
        pytest.param("fedora-rawhide", "s390x", id="fedora-rawhide-cross-s390x"),
    ],
)
def test_cross_platform_arch_mismatch(facts, test_project, target, arch):
    with pytest.raises(ProjectError):
        test_project.get_packages(facts[target], cross_arch=arch)
