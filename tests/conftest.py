import pytest

from pathlib import Path

from lcitool.config import Config
from lcitool.packages import Packages
from lcitool.projects import Projects
from lcitool.targets import Targets

import test_utils.utils as test_utils


def pytest_addoption(parser):
    parser.addoption(
        "--regenerate-output",
        help="regenerate output data set to reflect the changed inputs",
        default=False,
        action="store_true",
    )


def pytest_configure(config):
    opts = ["regenerate_output"]
    pytest.custom_args = {opt: config.getoption(opt) for opt in opts}


# These needs to be a global in order to compute ALL_PROJECTS and ALL_TARGETS
# at collection time.  Tests do not access it and use the fixtures below.
_PROJECTS = Projects()
_TARGETS = Targets()

ALL_PROJECTS = sorted(_PROJECTS.names + list(_PROJECTS.internal.keys()))
ALL_TARGETS = sorted(_TARGETS.targets)


@pytest.fixture
def config(monkeypatch, request, config_filename):
    actual_path = Path(test_utils.test_data_indir(request.module.__file__), config_filename)
    config = Config()

    # we have to monkeypatch the '_config_file_paths' attribute, since we don't
    # support custom inventory paths
    monkeypatch.setattr(config, "_config_file_paths", [actual_path])
    return config


@pytest.fixture(scope="module")
def packages():
    return Packages()


@pytest.fixture
def projects():
    return _PROJECTS


@pytest.fixture
def targets():
    return _TARGETS
