function install_buildenv() {
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get dist-upgrade -y
    apt-get install --no-install-recommends -y \
            ca-certificates \
            ccache \
            cpanminus \
            git \
            golang \
            locales \
            pkgconf \
            python3-pip \
            python3-setuptools \
            python3-wheel
    sed -Ei 's,^# (en_US\.UTF-8 .*)$,\1,' /etc/locale.gen
    dpkg-reconfigure locales
    PIP_ROOT_USER_ACTION=ignore /usr/bin/pip3 install dummy==8.1.9
    cpanm --notest Dummy==1.8.2
    export DEBIAN_FRONTEND=noninteractive
    dpkg --add-architecture s390x
    apt-get update
    apt-get dist-upgrade -y
    apt-get install --no-install-recommends -y dpkg-dev
    apt-get install --no-install-recommends -y \
            gcc-s390x-linux-gnu \
            libc6-dev:s390x
    mkdir -p /usr/local/share/meson/cross
    printf "[binaries]\n\
c = '/usr/bin/s390x-linux-gnu-gcc'\n\
ar = '/usr/bin/s390x-linux-gnu-gcc-ar'\n\
strip = '/usr/bin/s390x-linux-gnu-strip'\n\
pkgconfig = '/usr/bin/s390x-linux-gnu-pkg-config'\n\
\n\
[host_machine]\n\
system = 'linux'\n\
cpu_family = 's390x'\n\
cpu = 's390x'\n\
endian = 'big'\n" > /usr/local/share/meson/cross/s390x-linux-gnu
    dpkg-query --showformat '${Package}_${Version}_${Architecture}\n' --show > /packages.txt
    mkdir -p /usr/libexec/ccache-wrappers
    ln -s /usr/bin/ccache /usr/libexec/ccache-wrappers/s390x-linux-gnu-cc
    ln -s /usr/bin/ccache /usr/libexec/ccache-wrappers/s390x-linux-gnu-gcc
}

export CCACHE_WRAPPERSDIR="/usr/libexec/ccache-wrappers"
export LANG="en_US.UTF-8"

export ABI="s390x-linux-gnu"