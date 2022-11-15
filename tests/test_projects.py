# test_projects: test the project package definitions
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

from lcitool.projects import Projects
from lcitool.inventory import Inventory


_PROJECTS = Projects()
ALL_PROJECTS = sorted(_PROJECTS.names + list(_PROJECTS.internal_projects.keys()))


@pytest.fixture(params=ALL_PROJECTS)
def project(request):
    try:
        return _PROJECTS.projects[request.param]
    except KeyError:
        return _PROJECTS.internal_projects[request.param]


def test_project_packages(project):
    target = Inventory().targets[0]
    facts = Inventory().target_facts[target]
    project.get_packages(facts)


def test_project_package_sorting(project):
    pkgs = project._load_generic_packages()

    otherpkgs = sorted(pkgs)

    assert otherpkgs == pkgs
