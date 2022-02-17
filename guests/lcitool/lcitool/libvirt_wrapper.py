# libvirt_wrapper.py - module abstracting the libvirt library
#
# Copyright (C) 2022 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import libvirt
import logging
import textwrap

log = logging.getLogger(__name__)

LCITOOL_XMLNS = "http://libvirt.org/schemas/lcitool/1.0"


class LibvirtWrapperError(Exception):
    """
    Global exception type for this module.

    Contains a libvirt error message. On the application level, this is the
    exception type you should be catching.
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"LibvirtWrapper error: {self.message}"


class LibvirtWrapper():
    def __init__(self):
        def nop_error_handler(_T, iterable):
            return None

        # Disable libvirt's default console error logging
        libvirt.registerErrorHandler(nop_error_handler, None)
        self._conn = libvirt.open()

    def set_target(self, host, target):
        """Inject target OS to host's XML metadata."""

        xml = textwrap.dedent(
            f"""
            <host>
              <target>{target}</target>
            </host>
            """)

        try:
            dom = self._conn.lookupByName(host)
            dom.setMetadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT,
                            xml, "lcitool", LCITOOL_XMLNS,
                            flags=(libvirt.VIR_DOMAIN_AFFECT_CONFIG |
                                   libvirt.VIR_DOMAIN_AFFECT_LIVE))
        except libvirt.libvirtError as e:
            raise LibvirtWrapperError(
                f"Failed to set metadata for '{host}': " + str(e)
            )
