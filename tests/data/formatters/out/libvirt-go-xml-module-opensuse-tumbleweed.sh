function install_buildenv() {
    zypper dist-upgrade -y
    zypper install -y --allow-downgrade \
           ca-certificates \
           git \
           glibc-locale \
           go
    rpm -qa | sort > /packages.txt
}

export LANG="en_US.UTF-8"