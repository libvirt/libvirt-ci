function install_buildenv() {
    dnf --quiet update -y --nogpgcheck fedora-gpg-keys
    dnf --quiet distro-sync -y
    dnf --quiet install -y \
                ca-certificates \
                ccache \
                git \
                glibc-langpack-en \
                golang \
                perl-App-cpanminus \
                python3-pip \
                python3-setuptools \
                python3-wheel
    /usr/bin/pip3 install dummy==8.1.9
    cpanm --notest Dummy==1.8.2
    dnf --quiet install -y \
                mingw32-gcc \
                mingw32-headers \
                mingw32-pkg-config
    rpm -qa | sort > /packages.txt
    mkdir -p /usr/libexec/ccache-wrappers
    ln -s /usr/bin/ccache /usr/libexec/ccache-wrappers/i686-w64-mingw32-cc
    ln -s /usr/bin/ccache /usr/libexec/ccache-wrappers/i686-w64-mingw32-gcc
}

export CCACHE_WRAPPERSDIR="/usr/libexec/ccache-wrappers"
export LANG="en_US.UTF-8"

export ABI="i686-w64-mingw32"
