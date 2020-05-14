==========
libvirt CI
==========

This repository contains all information necessary to keep the Jenkins-based
`libvirt CI <https://ci.centos.org/view/libvirt/>`_ environment, hosted on the
CentOS CI infrastructure, running.

Configuration for the Jenkins jobs themselves can be found in the ``jenkins/``
directory, while tools for creating and managing the virtual machines such
jobs ultimately run on are in the ``guests/`` directory.

If you're a developer looking to reproduce and debug a failure reported by
the libvirt CI locally, then the ``guests/`` directory is what you're looking
for.
