# libvirt_wrapper.py - module abstracting the libvirt library
#
# Copyright (C) 2022 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import abc
import libvirt
import logging
import textwrap

import xml.etree.ElementTree as ET

from pathlib import Path

from lcitool import LcitoolError

log = logging.getLogger(__name__)

LCITOOL_XMLNS = "http://libvirt.org/schemas/lcitool/1.0"


class LibvirtWrapperError(LcitoolError):
    """
    Global exception type for this module.

    Contains a libvirt error message. On the application level, this is the
    exception type you should be catching.
    """

    def __init__(self, message):
        super().__init__(message, "LibvirtWrapper")


class LibvirtWrapper():
    def __init__(self):
        def nop_error_handler(_T, iterable):
            return None

        # Disable libvirt's default console error logging
        libvirt.registerErrorHandler(nop_error_handler, None)
        self._conn = libvirt.open()

    @property
    def hosts(self):
        """Return all lcitool hosts."""

        hosts = {}
        try:
            doms = self._conn.listAllDomains()
        except libvirt.libvirtError as e:
            raise LibvirtWrapperError("Failed to load libvirt domains: " + e)

        for dom in doms:
            try:
                xml = dom.metadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT,
                                   LCITOOL_XMLNS,
                                   libvirt.VIR_DOMAIN_AFFECT_CONFIG)
            except libvirt.libvirtError as e:
                if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN_METADATA:
                    # skip hosts which don't have lcitool's metadata
                    continue

                raise LibvirtWrapperError(
                    f"Failed to query metadata for '{dom.name}': " + str(e)
                )

            xmltree = ET.fromstring(xml)
            target = xmltree.find("target")
            if xmltree.tag != "host" or target is None or target.text is None:
                continue

            hosts[dom.name()] = target.text

        return hosts

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


class LibvirtAbstractObject(abc.ABC):
    """
    Libvirt's vir<Any> obj wrapper base class.

    The wrapper object defines convenience methods and attribute shortcuts
    extracting data from libvirt's XML descriptions. To use the wrapped object
    directly, the libvirt object is available in the 'raw' attribute.

    Attributes:
        :ivar raw: Raw libvirt vir<Any> object

    """

    def __init__(self, obj):
        self.raw = obj

    def _get_xml_tree(self):
        return ET.fromstring(self.raw.XMLDesc())

    def _get_xml_node(self, node_name, root=None):
        if root is None:
            root = self._get_xml_tree()

        nodeelem = root.find(node_name)
        return nodeelem.text


class LibvirtPoolObject(LibvirtAbstractObject):

    def __init__(self, obj):
        super().__init__(obj)
        self._path = None

    @property
    def path(self):
        if self._path is None:
            self._path = self._get_xml_node("target/path")
        return Path(self._path)
