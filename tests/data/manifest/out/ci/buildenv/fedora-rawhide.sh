function install_buildenv() {
    dnf --quiet update -y --nogpgcheck fedora-gpg-keys
    dnf --quiet distro-sync -y
    dnf --quiet install -y \
                ca-certificates \
                ccache \
                gcc \
                git \
                glibc-devel \
                glibc-langpack-en \
                golang \
                perl-App-cpanminus \
                pkgconfig \
                python3-pip \
                python3-setuptools \
                python3-wheel
    rpm -qa | sort > /packages.txt
    mkdir -p /usr/libexec/ccache-wrappers
    ln -s /usr/bin/ccache /usr/libexec/ccache-wrappers/cc
    ln -s /usr/bin/ccache /usr/libexec/ccache-wrappers/gcc
    PIP_ROOT_USER_ACTION=ignore /usr/bin/pip3 install dummy==8.1.9
    cpanm --notest Dummy==1.8.2
}

export CCACHE_WRAPPERSDIR="/usr/libexec/ccache-wrappers"
export LANG="en_US.UTF-8"
