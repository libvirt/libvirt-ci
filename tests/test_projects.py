# test_projects: test the project package definitions
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

from lcitool.inventory import Inventory
from lcitool.projects import Projects


# This needs to be a global in order to compute ALL_PROJECTS at collection
# time.  Tests do not access it and use the fixtures below.
_PROJECTS = Projects()
ALL_PROJECTS = sorted(_PROJECTS.names + list(_PROJECTS.internal.keys()))


@pytest.fixture(scope="module")
def inventory():
    return Inventory()


@pytest.fixture(scope="module")
def projects():
    return _PROJECTS


@pytest.fixture(params=ALL_PROJECTS)
def project(request, projects):
    try:
        return projects.public[request.param]
    except KeyError:
        return projects.internal[request.param]


def test_project_packages(inventory, project):
    target = inventory.get_target(inventory.targets[0])
    project.get_packages(target)


def test_project_package_sorting(project):
    pkgs = project._load_generic_packages()

    otherpkgs = sorted(pkgs)

    assert otherpkgs == pkgs
