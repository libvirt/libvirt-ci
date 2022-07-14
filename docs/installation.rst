Installation
============

Installing dependencies
-----------------------

``virt-install`` need to be available on the host. Since it is not distributed
via PyPI, this needs to be installed with your package manager.

You need to install also a few Python dependencies using your package manager
or using ``pip3`` (see the provided ``requirements.txt`` file). You can install
to the Python user install directory

::

   # this will install only the very basic dependencies
   $ pip3 install --user -r requirements.txt

or, system-wide

::

   # this will install only the very basic dependencies
   $ sudo pip3 install -r requirements.txt

Depending on your intended use case for lcitool you can pick which dependencies
you need to have installed, e.g.

If you want to create and manage VMs for your CI workloads with ``lcitool``,
you will need more than just the very basic dependencies:

::

   $ pip3 install --user -r vm-requirements.txt

or if you want to contribute to the project, you'll need the largest set
containing even the test dependencies

::

   $ pip3 install --user -r test-requirements.txt


.. note:: If you prefer you can try to find those requirements in your package
   manager as well.

Installing lcitool
------------------

This is a standard python package, so you can install it either as your local
user

::

   $ python3 setup.py install --user

or system-wide with

::

   $ sudo python3 setup.py install

If you prefer, you can have it installed inside a virtual-env too.

For development purposes you may find convenient to do

::

   $ python3 setup.py develop --user

which will create the necessary links to your working directory and so you
won't need to re-install the lcitool package locally after every code change.

If you don't want to install this tool into your environment and instead wish
to run it directly, just run the `bin/lcitool` script that is located at the
root of this repository.
