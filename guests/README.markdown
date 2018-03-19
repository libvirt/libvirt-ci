libvirt CI - guest management tools
===================================

The tools contained in this directory simplify and automate the management
of the guests used by the Jenkins-based libvirt CI environment.

There are two steps to bringing up a guest:

* `./lcitool install $guest` will perform an unattended installation
  of `$guest`. Not all guests can be installed this way: see the "FreeBSD"
  section below;

* `./lcitool prepare $guest` will go through all the post-installation
  configuration steps required to make the newly-created guest usable;

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


Test use
---------------

If you are a developer trying to reproduce a bug on some OS you don't
have easy access to, you can use these tools to create a suitable test
environment.

The `test` flavor is used by default, so you don't need to do anything
special in order to use it: just follow the steps outlined above. Once
a guest has been prepared, you'll be able to log in as `test` either
via SSH (your public key will have been authorized) or on the serial
console (password: `test`).

Once logged in, you'll be able to perform administrative tasks using
`sudo`. Regular root access will still be available, either through
SSH or on the serial console.

Since guests created for this purpose are probably not going to be
long-lived or contain valuable information, you can configure your
SSH client to skip some of the usual verification steps and thus
prompt you less frequently; moreover, you can have the username
selected automatically for you to avoid having to type it in every
single time you want to connect. Just add

    Host libvirt-*
        User test
        GSSAPIAuthentication no
        StrictHostKeyChecking no
        CheckHostIP no
        UserKnownHostsFile /dev/null

to your `~/.ssh/config` file to achieve all of the above.


Jenkins CI use
--------------

You'll need to configure `lcitool` to use the `jenkins` flavor for
guests: to do so, just write `jenkins` in the `~/.config/lcitool/flavor`
file.

Once a guest has been prepared, you'll be able to log in as root either
via SSH (your public key will have been authorized) or on the serial
console (using the password configured earlier).


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


Adding new guests
-----------------

Adding new guests will require tweaking the inventory and host variables,
but it should be very easy to eg. use the Fedora 26 configuration to come
up with a working Fedora 27 configuration.
