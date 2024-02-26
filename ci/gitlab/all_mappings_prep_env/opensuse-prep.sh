#!/bin/sh

zypper dist-upgrade -y
zypper install -y \
    perl-App-cpanminus \
    python311-base \
    python311-pip
