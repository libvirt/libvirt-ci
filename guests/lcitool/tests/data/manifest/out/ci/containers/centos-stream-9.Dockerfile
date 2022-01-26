FROM quay.io/centos/centos:stream9

RUN dnf update -y && \
    dnf install 'dnf-command(config-manager)' -y && \
    dnf config-manager --set-enabled -y crb && \
    dnf install -y \
        https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm \
        https://dl.fedoraproject.org/pub/epel/epel-next-release-latest-9.noarch.rpm && \
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
