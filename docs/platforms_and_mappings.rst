Adding a new target OS
======================

If you want to contribute a new target OS to lcitool, you'll have to create
a directory with the corresponding name under the
``lcitool/ansible/group_vars`` and place a YAML configuration of
the target OS inside. The structure of the configuration file should correspond
with the other targets, so please follow them by example.
Unless your desired target OS uses a packaging format which lcitool can't work
with yet, you're basically done, just record the OS name in the
``lcitool/ansible/vars/mappings.yml`` file in the commentary
section at the beginning of the file - again, follow the existing entries by
example. However, if you're introducing a new packaging format, you'll have to
update **all** the mappings in the file so that lcitool knows what the name of
a specific package is on your target OS.
