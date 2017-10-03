Ansible playbooks for libvirt CI
================================

These can be used to turn a freshly installed machine into a worker for
the Jenkins-based libvirt CI.

There are two main playbooks:

* `bootstrap.yml`, used to perform the bootstrapping phase, that is, getting
  guests to the point where Ansible can manage them fully and prompting the
  user for a password is no longer required;

* `site.yml`, used for the remaining configuration steps.

Although you can use the playbooks directly, it's much more convenient to
call either `make bootstrap` or `make site` instead.

Each guest only needs to be bootstrapped once; that said, both playbooks are
idempotent so there's no harm in applying them over and over again.


Requirements
------------

SSH must be running in the guest, and root login must be permitted.


CI use
------

After you have reinstalled a Jenkins worker, run `make bootstrap` followed
by `make site` and a reboot to get it ready for CI use. No further action
should be necessary.

Adding new workers will require tweaking the inventory and host variables,
but it should be very easy to eg. use the Fedora 26 configuration to come
up with a working Fedora 27 configuration.


Development use
---------------

If you are a developer trying to reproduce a bug on some OS you don't have
easy access to, you can use these playbooks to create a suitable test
environment.

Since the playbooks are intended mainly for CI use, you'll have to tweak them
a bit first, including:

* trimming down the `inventory` file to just the guest you're interested in;

* removing any references to the `jenkins` pseudo-project from
  `host_vars/$guest/main.yml`, along with any references to projects you're
  not interested to (this will cut down on the number of packages installed)
  and any references to `jenkins_secret`;

* deleting `host_vars/$guest/vault.yml` altogether.

After performing these tweaks, you should be able to just run `make bootstrap`
followed by `make site` as usual.
