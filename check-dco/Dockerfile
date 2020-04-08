FROM centos:8

RUN dnf -y install python3 git && \
    dnf -y clean all

COPY check-dco.py /check-dco
