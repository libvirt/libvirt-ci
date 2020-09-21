import os

from setuptools import setup, Command


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system("rm -vrf ./build ./dist ./*.pyc ./*.egg-info")


setup(
    name="lcitool",
    version="0.1",
    packages=["lcitool"],
    scripts=["bin/lcitool"],
    author="libvirt team",
    author_email="libvir-list@redhat.com",
    description="libvirt CI guest management tool",
    keywords="libvirt ci",
    url="https://libvirt.org",
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)"
    ],
    cmdclass={
        "clean": CleanCommand,
    }
)
