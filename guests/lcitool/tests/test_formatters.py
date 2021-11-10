# test_formatters: test the formatters
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

import test_utils.utils as test_utils
from pathlib import Path

from lcitool import util
from lcitool.formatters import ShellVariablesFormatter, DockerfileFormatter


scenarios = [
    # A minimalist application, testing package managers
    pytest.param("test-minimal", "debian-10", None, id="minimal-debian-10"),
    pytest.param("test-minimal", "centos-8", None, id="minimal-centos-8"),
    pytest.param("test-minimal", "opensuse-leap-152", None, id="minimal-opensuse-leap-152"),
    pytest.param("test-minimal", "alpine-314", None, id="minimal-alpine-314"),

    # A minimalist application, testing two different cross-compile scenarios
    pytest.param("test-minimal", "debian-10", "s390x", id="minimal-debian-10-cross-s390x"),
    pytest.param("test-minimal", "fedora-rawhide", "mingw64", id="minimal-fedora-rawhide-cross-mingw64"),

    # An application using cache symlinks
    pytest.param("test-ccache", "debian-10", None, id="ccache-debian-10"),
    pytest.param("test-ccache", "debian-10", "s390x", id="ccache-debian-10-cross-s390x"),
]


@pytest.mark.parametrize("project,target,arch", scenarios)
def test_dockerfiles(project, target, arch, request):
    util.set_extra_data_dir(test_utils.test_data_dir(__file__))
    gen = DockerfileFormatter()
    actual = gen.format(target, [project], arch)
    expected_path = Path(test_utils.test_data_outdir(__file__), request.node.callspec.id + ".Dockerfile")
    test_utils.assert_matches_file(actual, expected_path)


@pytest.mark.parametrize("project,target,arch", scenarios)
def test_variables(project, target, arch, request):
    util.set_extra_data_dir(test_utils.test_data_dir(__file__))
    gen = ShellVariablesFormatter()
    actual = gen.format(target, [project], arch)
    expected_path = Path(test_utils.test_data_outdir(__file__), request.node.callspec.id + ".vars")
    test_utils.assert_matches_file(actual, expected_path)
