libvirt CI - guest management tools
===================================

The tools contained in this directory simplify and automate the management
of the guests used by the Jenkins-based libvirt CI environment.


Usage and examples
------------------

There are two steps to bringing up a guest:

* `lcitool install $guest` will perform an unattended installation
  of `$guest`. Not all guests can be installed this way: see the "FreeBSD"
  section below;

* `lcitool update $guest $project` will go through all the
  post-installation configuration steps required to make the newly-created
  guest usable and ready to be used for building `$project`;

Once those steps have been performed, maintenance will involve running:

    lcitool update $guest $project

periodically to ensure the guest configuration is sane and all installed
packages are updated.

To get a list of known guests and projects, run

    lcitool hosts

and

    lcitool projects

respectively. You can run operations involving multiple guests and projects
at once by providing a list on the command line: for example, running

    lcitool update '*fedora*' '*osinfo*'

will update all Fedora guests and get them ready to build libosinfo and
related projects, while running

    lcitool update all 'libvirt,libvirt+mingw*'

will update all hosts and prepare them to build libvirt both as a native
library and, where supported, as a Windows library using MinGW.

Once hosts have been prepared following the steps above, you can use
`lcitool` to perform builds as well: for example, running

    lcitool build '*debian*' libvirt-python

will fetch libvirt-python's `master` branch from the upstream repository
and build it on all Debian hosts.

You can add more git repositories by tweaking the `git_urls` dictionary
defined in `playbooks/build/jobs/defaults.yml` and then build arbitrary
branches out of those with

    lcitool build -g github/cool-feature all libvirt


Host setup
----------

`ansible` and `virt-install` need to be available on the host, the former can
be either installed system-wide using your package manager or using `pip`
(see the provided requirements.txt file). The latter can only be installed with
your package manager as `virt-install` is not distributed via PyPI.

Before you can start bringing up guests, you need to create
~/.config/lcitool/config.yaml, ideally by copying the `config.yaml` template,
and set at least the options marked as "(mandatory)" depending on the flavor
(`test`, `jenkins`, `gitlab`) you wish to use with your machines.

Ansible expects to be able to connect to the guests by name: installing and
enabling the [libvirt NSS plugin](https://wiki.libvirt.org/page/NSS_module)
on the host is the easiest way to make sure that works. More specifically,
you'll want to use the `libvirt_guest` variant of the plugin.

To keep guests up to date over time, it's recommended to have an entry
along the lines of

    0 0 * * * ~/libvirt-ci/guests/lcitool update all all

in your crontab.


Test use
--------

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
guests. To do so, simply set the `install.flavor` to `jenkins` in
`~/.config/lcitool/config.yaml`.

Once a guest has been prepared, you'll be able to log in as root either
via SSH (your public key will have been authorized) or on the serial
console (using the password configured earlier).


FreeBSD
-------

Installation of FreeBSD guests must be performed manually; alternatively,
the official qcow2 images can be used to quickly bring up such guests.

    $ MAJOR=12
    $ MINOR=1
    $ VER=$MAJOR.$MINOR-RELEASE
    $ sudo wget -O /var/lib/libvirt/images/libvirt-freebsd-$MAJOR.qcow2.xz \
      https://download.freebsd.org/ftp/releases/VM-IMAGES/$VER/amd64/Latest/FreeBSD-$VER-amd64.qcow2.xz
    $ sudo unxz /var/lib/libvirt/images/libvirt-freebsd-$MAJOR.qcow2.xz
    $ virt-install \
      --import \
      --name libvirt-freebsd-$MAJOR \
      --vcpus 2 \
      --graphics vnc \
      --noautoconsole \
      --console pty \
      --sound none \
      --rng device=/dev/urandom,model=virtio \
      --memory 2048 \
      --os-variant freebsd$MAJOR.0 \
      --disk /var/lib/libvirt/images/libvirt-freebsd-$MAJOR.qcow2

The default qcow2 images are sized too small to be usable. To enlarge
them do

    $ virsh blockresize libvirt-freebsd-$MAJOR \
      /var/lib/libvirt/images/libvirt-freebsd-$MAJOR.qcow2 15G

Then inside the guest, as root, enlarge the 3rd partition & filesystem
to consume all new space:

    # gpart resize -i 3 vtbd0
    # service growfs onestart

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
