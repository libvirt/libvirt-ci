# osinfo.py - wraps OSInfoDB functionality
#
# Copyright (C) 2023 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import abc

from gi.repository import Libosinfo


class OSinfoAbstractObject(abc.ABC):
    def __init__(self, obj):
        self.raw = obj


class OSinfoDB():
    def __init__(self):
        loader = Libosinfo.Loader()
        loader.process_default_path()
        self._db = loader.get_db()
