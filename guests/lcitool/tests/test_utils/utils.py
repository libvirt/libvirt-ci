# utils: a set of test suite utility functions
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest
import yaml


def assert_matches_file(actual, expected_path):
    if pytest.custom_args["regenerate_output"]:
        # Make sure the target directory exists, since creating the
        # output file would fail otherwise
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_path, "w") as fd:
            yaml.safe_dump(actual, stream=fd)

    with open(expected_path) as fd:
        expected = yaml.safe_load(fd)

    assert actual.keys() == expected.keys()
    for key in actual.keys():
        assert actual[key] == expected[key]
