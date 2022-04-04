#!/bin/sh

cargo clippy --quiet --no-deps --all-targets > cargo-clippy.txt

if test -s cargo-clippy.txt
then
    echo
    echo "❌ ERROR: some files failed cargo clippy code style check"
    echo
    echo "See the cargo-clippy.txt artifact for full details of mistakes."
    echo
    exit 1
fi

echo "✔ OK: all files passed cargo clippy code style check"
