import logging

from .containers import Container, ContainerError

log = logging.getLogger()


class PodmanBuildError(ContainerError):
    """
    Thrown whenever error occurs during
    podman build operation.
    """
    pass


class PodmanRunError(ContainerError):
    """
    Thrown whenever error occurs during
    podman run operation.
    """
    pass


class Podman(Container):
    """Podman container class"""

    def __init__(self):
        super().__init__()
        self._run_exception = PodmanRunError
        self._build_exception = PodmanBuildError

    def _extra_args(self, user):
        """
        Get Podman specific host namespace mapping
        :param user: numerical ID (int) or username (str) of the user.

        :returns: a list of id mapping
        """

        # Podman cannot reuse host namespace when running non-root
        # containers.  Until support for --keep-uid is added we can
        # just create another mapping that will do that for us.
        # Beware, that in {uid,gid}map=container_id:host_id:range, the
        # host_id does actually refer to the uid in the first mapping
        # where 0 (root) is mapped to the current user and rest is
        # offset.
        #
        # In order to set up this mapping, we need to keep all the
        # user IDs to prevent possible errors as some images might
        # expect UIDs up to 90000 (looking at you fedora), so we don't
        # want the overflowuid to be used for them.  For mapping all
        # the other users properly, some math needs to be done.
        # Don't worry, it's just addition and subtraction.
        #
        # 65536 ought to be enough (tm), but for really rare cases the
        # maximums might need to be higher, but that only happens when
        # your /etc/sub{u,g}id allow users to have more IDs.  Unless
        # --keep-uid is supported, let's do this in a way that should
        # work for everyone.

        podman_args_ = []

        _, _, uid, gid, _, _, _ = self._passwd(user)
        if uid == 0:
            return podman_args_

        max_uid = int(open("/etc/subuid").read().split(":")[-1])
        max_gid = int(open("/etc/subgid").read().split(":")[-1])

        if max_uid is None:
            max_uid = 65536
        if max_gid is None:
            max_gid = 65536

        uid_other = uid + 1
        gid_other = gid + 1
        uid_other_range = max_uid - uid
        gid_other_range = max_gid - gid

        podman_args_.extend([
            "--uidmap", f"0:1:{uid}",
            "--uidmap", f"{uid}:0:1",
            "--uidmap", f"{uid_other}:{uid_other}:{uid_other_range}",
            "--gidmap", f"0:1:{gid}",
            "--gidmap", f"{gid}:0:1",
            "--gidmap", f"{gid_other}:{gid_other}:{gid_other_range}"
        ])
        return podman_args_
