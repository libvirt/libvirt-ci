# package.py - module resolving package mappings to real-world package names
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Translates generic package mapping names to concrete package names

This module takes care of translation of the generic package mapping names
originating from the mappings.yml file (e.g. ansible/vars/mappings.yml) to
specific package names depending on several factors like packaging format, OS
distribution, cross building, etc.

Each package is represented by the abstract Package class which serves as a
base class for the specific package type subclasses (see the hierarchy below).

                            +-------------------+
                            |      Package      |
                            +-------------------+
             _______________|    |         |    |_____________
            |                    |         |                  |
+-----------v--+    +------------v--+    +-v-----------+    +-v-----------+
| CrossPackage |    | NativePackage |    | PyPIPackage |    | CPANPackage |
+--------------+    +---------------+    +-------------+    +-------------+

Exported classes:
    - Package
    - NativePackage
    - CrossPackage
    - PyPIPackage
    - CPANPackage
    - PackageFactory
"""


import abc
import logging

from lcitool import util

log = logging.getLogger(__name__)


class PackageError(Exception):
    """
    Global exception type for the package module.

    Contains a detailed message coming from one of its subclassed exception
    types. On the application level, this is the exception type you should be
    catching instead of the subclassed types.
    """

    def __str__(self):
        return f"Package generic name resolution failed: {self.message}"


class PackageEval(PackageError):
    """Thrown when the generic name could not be resolved with the given package type"""

    def __init__(self, message):
        self.message = message


class MappingKeyNotFound(Exception):
    """Thrown when the given mapping key could not be matched in the mappings file"""
    pass


class Package(metaclass=abc.ABCMeta):
    """
    Abstract base class for all package types

    This class defines the public interface for all its subclasses:
        - NativePackage
        - CrossPackage
        - PyPIPackage
        - CPANPackage

    Attributes:
        :ivar name: the actual package name
        :ivar mapping: the generic package name that will resolve to @name
    """

    def __init__(self, pkg_mapping):
        """
        Initialize the package with a generic package name

        :param pkg_mapping: name of the package mapping to resolve
        """

        self.mapping = pkg_mapping
        self.name = None

    @abc.abstractmethod
    def _eval(self, mappings, key="default"):
        """
        Resolves package mapping to the actual name of the package.

        This method modifies the internal state of the instance. Depending on
        what packaging system needs to be used to resolve the given mapping
        the instance's name public attribute will be filled in accordingly.

        :param mappings: dictionary of generic package name mappings
        :param key: which subkey to look for in a given package mapping,
                    e.g. key='rpm', key='CentOS', key='cross-mingw32-rpm', etc.
        :return: name of the resolved package as string, can be None if the
                 package is supposed to be disabled on the given platform
        :raises: MappingKeyNotFound
        """

        log.debug(f"Eval of mapping='{self.mapping}', key='{key}'")

        mapping = mappings.get(self.mapping, {})
        try:
            return mapping[key]
        except KeyError:
            raise MappingKeyNotFound


class CrossPackage(Package):

    def __init__(self,
                 mappings,
                 pkg_mapping,
                 pkg_format,
                 base_keys,
                 cross_arch):

        super().__init__(pkg_mapping)

        self.name = self._eval(mappings, pkg_format, base_keys, cross_arch)
        if self.name is None:
            raise PackageEval(f"No mapping for '{pkg_mapping}'")

    def _eval(self, mappings, pkg_format, base_keys, cross_arch):
        cross_keys = ["cross-" + cross_arch + "-" + k for k in base_keys]

        if pkg_format == "deb":
            # For Debian-based distros, the name of the foreign package
            # is usually the same as the native package, but there might
            # be architecture-specific overrides, so we have to look both
            # at the neutral keys and at the specific ones
            arch_keys = [cross_arch + "-" + k for k in base_keys]
            cross_keys.extend(arch_keys + base_keys)

        pkg_name = None
        for k in cross_keys:
            try:
                pkg_name = super()._eval(mappings, key=k)
                if pkg_name is None:
                    return None

                if pkg_format == "deb":
                    # For Debian-based distros, the name of the foreign package
                    # is obtained by appending the foreign architecture (in
                    # Debian format) to the name of the native package.
                    #
                    # The exception to this is cross-compilers, where we have
                    # to install the package for the native architecture in
                    # order to be able to build for the foreign architecture
                    cross_arch_deb = util.native_arch_to_deb_arch(cross_arch)
                    if self.mapping not in ["gcc", "g++"]:
                        pkg_name = pkg_name + ":" + cross_arch_deb
                return pkg_name
            except MappingKeyNotFound:
                continue


class NativePackage(Package):

    def __init__(self,
                 mappings,
                 pkg_mapping,
                 base_keys):

        super().__init__(pkg_mapping)

        self.name = self._eval(mappings, base_keys)
        if self.name is None:
            raise PackageEval(f"No mapping for '{pkg_mapping}'")

    def _eval(self, mappings, base_keys):
        native_arch = util.get_native_arch()
        native_keys = [native_arch + "-" + k for k in base_keys] + base_keys

        for k in native_keys:
            try:
                return super()._eval(mappings, key=k)
            except MappingKeyNotFound:
                continue


class PyPIPackage(Package):

    def __init__(self,
                 mappings,
                 pkg_mapping):

        super().__init__(pkg_mapping)

        self.name = self._eval(mappings)
        if self.name is None:
            raise PackageEval(f"No mapping for '{pkg_mapping}'")

    def _eval(self, mappings):
        try:
            return super()._eval(mappings)
        except MappingKeyNotFound:
            return None


class CPANPackage(Package):

    def __init__(self,
                 mappings,
                 pkg_mapping):

        super().__init__(pkg_mapping)

        self.name = self._eval(mappings)
        if self.name is None:
            raise PackageEval(f"No mapping for '{pkg_mapping}'")

    def _eval(self, mappings):
        try:
            return super()._eval(mappings)
        except MappingKeyNotFound:
            return None
