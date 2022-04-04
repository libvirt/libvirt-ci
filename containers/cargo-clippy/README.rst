===================================================
Container for running cargo clippy code style check
===================================================

This container provides a simple way to invoke ``cargo clippy`` to validate
code style across a Rust codebase. It should be integrated into CI by setting
the following flag in ``ci/manifest.yml``

::

   gitlab:
     jobs:
       cargo-clippy: true

or adding the following snippet to ``.gitlab-ci.yml``

::

   cargo-clippy:
     stage: sanity_checks
     image: registry.gitlab.com/libvirt/libvirt-ci/cargo-clippy:master
     needs: []
     script:
       - /cargo-clippy
     artifacts:
       paths:
         - cargo-clippy.txt
       expire_in: 1 week
       when: on_failure
