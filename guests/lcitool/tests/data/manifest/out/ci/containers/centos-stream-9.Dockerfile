FROM quay.io/centos/centos:stream9

RUN dnf distro-sync -y && \
    dnf install 'dnf-command(config-manager)' -y && \
    dnf config-manager --set-enabled -y crb && \
    dnf install -y epel-release && \
    dnf install -y epel-next-release && \
    dnf install -y \
        ca-certificates \
        gcc \
        git \
        glib2-devel \
        glibc-langpack-en \
        gtk-doc \
        pkgconfig && \
    dnf autoremove -y && \
    dnf clean all -y && \
    rpm -qa | sort > /packages.txt

ENV LANG "en_US.UTF-8"
