#!/usr/bin/env python3

import yaml

with open("ansible/vars/mappings.yml", "r") as infile:
    mappings = yaml.safe_load(infile).get("mappings")

native_names = []
cross_names = []

for name, mapping in mappings.items():
    cross = False
    for key, value in mapping.items():
        if key.startswith("cross-policy-") and value == "foreign":
            cross = True
    if cross:
        cross_names.extend([name])
    else:
        native_names.extend([name])

print(f"native_names: {native_names}")
print(len(native_names))
print(f"cross_names: {cross_names}")
print(len(cross_names))
