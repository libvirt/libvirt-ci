import pwd
import pytest

from io import TextIOBase
from _pytest.monkeypatch import MonkeyPatch
from test_utils.utils import assert_equal_list

from lcitool.containers import ContainerError, Podman


id_mapping = [
    "--uidmap", "0:1:100",
    "--uidmap", "100:0:1",
    "--uidmap", "101:101:5900",
    "--gidmap", "0:1:100",
    "--gidmap", "100:0:1",
    "--gidmap", "101:101:5900"
]


def get_pwuid(id):
    """Mock funtion for pwd.getpwuid"""

    root_user = ["root", "x", 0, 0, "Mr root", "/root", "/bin/sh"]
    test_user = ["user", "x", 100, 100, "Mr user", "/home/user", "/bin/sh"]
    db = {"root": root_user, 0: root_user, 1: test_user, "user": test_user}
    return db[id]


class MockSubUidGidTextIO(TextIOBase):
    """Mock class for builtins.open"""

    def __init__(self, file, **kwargs):
        pass

    def read(self, *kwargs):
        # we only care about the last column for id mapping
        # (this is the only item we need in Podman._extra_args)
        return "_:_:6000"


@pytest.fixture(scope="module")
def mock_pwd():
    monkeypatch = MonkeyPatch()
    monkeypatch.setattr(pwd, "getpwuid", get_pwuid)
    monkeypatch.setattr(pwd, "getpwnam", get_pwuid)
    yield monkeypatch
    monkeypatch.undo()


@pytest.fixture(scope="module")
def podman():
    return Podman()


class TestPodmanExtraArgs:
    """Unit test for Podman()._extra_args"""

    @staticmethod
    def mock_open(file, **kwargs):
        return MockSubUidGidTextIO(file, **kwargs)

    @pytest.fixture(scope="class", autouse=True)
    def patch_builtins_open(self):
        monkeypatch = MonkeyPatch()
        monkeypatch.setattr("builtins.open", TestPodmanExtraArgs.mock_open)
        yield monkeypatch
        monkeypatch.undo()

    @pytest.mark.parametrize(
        "user, args",
        [
            pytest.param(0, [], id="root-numeric-id"),
            pytest.param("root", [], id="root-string-id"),
            pytest.param(1, id_mapping, id="testuser-numeric-id"),
            pytest.param("user", id_mapping, id="testuser-string-id")
        ]
    )
    def test_podman_extra_args(self, user, args, mock_pwd, podman):
        assert_equal_list(podman._extra_args(user), args, [], "item")

    @pytest.mark.parametrize(
        "user, exception",
        [
            pytest.param(None, TypeError, id="NoneType-user"),
            pytest.param([], TypeError, id="non-string-and-numeric-user"),
            pytest.param("nonexistent", ContainerError, id="nonexistent-user"),
        ]
    )
    def test_extra_args_invalid_input(self, user, exception, mock_pwd, podman):
        with pytest.raises(exception):
            podman._extra_args(user)
