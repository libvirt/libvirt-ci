function install_buildenv() {
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get dist-upgrade -y
    apt-get install --no-install-recommends -y \
            ca-certificates \
            ccache \
            cpanminus \
            gcc \
            git \
            golang \
            libc6-dev \
            locales \
            pkgconf \
            python3-pip \
            python3-setuptools \
            python3-wheel
    sed -Ei 's,^# (en_US\.UTF-8 .*)$,\1,' /etc/locale.gen
    dpkg-reconfigure locales
    dpkg-query --showformat '${Package}_${Version}_${Architecture}\n' --show > /packages.txt
    mkdir -p /usr/libexec/ccache-wrappers
    ln -s /usr/bin/ccache /usr/libexec/ccache-wrappers/cc
    ln -s /usr/bin/ccache /usr/libexec/ccache-wrappers/gcc
    /usr/bin/pip3 install dummy==8.1.9
    cpanm --notest Dummy==1.8.2
}

export CCACHE_WRAPPERSDIR="/usr/libexec/ccache-wrappers"
export LANG="en_US.UTF-8"