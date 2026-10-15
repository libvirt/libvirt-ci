FROM quay.io/centos/centos:stream9

RUN dnf --quiet distro-sync -y && \
    dnf --quiet install 'dnf-command(config-manager)' -y && \
    dnf --quiet config-manager --set-enabled -y crb && \
    dnf --quiet install -y epel-release && \
    dnf --quiet install -y epel-next-release && \
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
                python3-wheel && \
    dnf --quiet autoremove -y && \
    dnf --quiet clean all -y && \
    rpm -qa | sort > /packages.txt && \
    mkdir -p /usr/libexec/ccache-wrappers && \
    ln -s /usr/bin/ccache /usr/libexec/ccache-wrappers/cc && \
    ln -s /usr/bin/ccache /usr/libexec/ccache-wrappers/gcc

RUN PIP_ROOT_USER_ACTION=ignore /usr/bin/pip3 install dummy==8.1.9

RUN cpanm --notest Dummy==1.8.2

ENV CCACHE_WRAPPERSDIR="/usr/libexec/ccache-wrappers"
ENV LANG="en_US.UTF-8"
