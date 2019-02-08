libvirt CI - Jenkins configuration
==================================

This directory contains jobs definitions for the libvirt Jenkins CI.

They're supposed to be fed to the Jenkins Job Builder tool, which can
be installed either through your distribution's package manager, for
example using:

    # dnf install python3-jenkins-job-builder

on Fedora, or straight from pip using:

    $ pip install --user jenkins-job-builder

The `jobs/` directory contains general templates for defining jobs
for the different build systems, such as GNU `autotools`, Python's
`distutils`, Perl's `ExtUtils::MakeMaker` and so on.

The `projects/` directory contains the per-project config which
activates the desired jobs and configures them if needed.

It's possible to see the raw Jenkins configuration using either:

    $ jenkins-jobs test -r .

to see al jobs, or:

    $ jenkins-jobs test -r . libvirt-master-build

if you're interested in a single job.

In order to apply the updated configuration on the server, you're
going to need a configuration file containing access information:

    $ cat jenkins.ini
    [jenkins]
    user=XXX
    password=XXX
    url=https://ci.centos.org

To update the Jenkins server with all jobs, run:

    $ jenkins-jobs --conf jenkins.ini update -r .
