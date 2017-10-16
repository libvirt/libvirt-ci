libvirt CI - guest management tools
===================================

The tools contained in this directory simplify and automate the management
of the guests used by the Jenkins-based libvirt CI environment.

There are two steps to bringing up a guest:

* `./lcitool install $guest` will perform an unattended installation
  of `$guest`. Not all guests can be installed this way: see the "FreeBSD"
  section below;

* `./lcitool prepare $guest` will go through all the post-installation
  configuration steps required to make the newly-created guest usable as
  part of the Jenkins CI setup.

Once those steps have been performed, maintainance will involve running:

* `./lcitool update $guest`

periodically to ensure the guest configuration is sane and all installed
packages are updated.


Host setup
----------

Ansible and `virt-install` need to be available on the host.

Before you can start bringing up guests, you'll have to store your
site-specific root password in the `~/.config/lcitool/root-password` file.
This password will only be necessary for serial console access in case
something goes horribly wrong; for day to day operations, SSH key
authentication will be used instead.

Ansible expects to be able to connect to the guests by name: installing and
enabling the [libvirt NSS plugin](https://wiki.libvirt.org/page/NSS_module)
on the host is the easiest way to make sure that works. More specifically,
you'll want to use the `libvirt_guest` variant of the plugin.

To keep guests up to date over time, it's recommended to have an entry
along the lines of

    0 0 * * * cd ~/libvirt-jenkins-ci/guests && ./lcitool update all

in your crontab.


Adding new guests
-----------------

Adding new guests will require tweaking the inventory and host variables,
but it should be very easy to eg. use the Fedora 26 configuration to come
up with a working Fedora 27 configuration.


Development use
---------------

If you are a developer trying to reproduce a bug on some OS you don't
have easy access to, you can use these tools to create a suitable test
environment.

Since the tools are intended mainly for CI use, you'll have to tweak them
a bit first, including:

* trimming down the `inventory` file to just the guest you're interested in;

* removing any references to the `jenkins` pseudo-project from
  `host_vars/$guest/main.yml`, along with any references to projects you're
  not interested to (this will cut down on the number of packages installed)
  and any references to `jenkins_secret`;

* deleting `host_vars/$guest/vault.yml` altogether.

After performing these tweaks, you should be able to use the same steps
outlined above.

A better way to deal with this use case will be provided in the future.


FreeBSD
-------

Installation of FreeBSD guests must be performed manually; alternatively,
the official qcow2 images can be used to quickly bring up such guests.

Some manual tweaking will be needed, in particular:

* `/etc/ssh/sshd_config` must contain the `PermitRootLogin yes` directive;

* `/etc/rc.conf` must contain the `sshd_enable="YES"` setting;

* the root password must be manually set to "root" (without quotes).

Once these steps have been performed, FreeBSD guests can be managed just
like all other guests.
