FROM centos:8

RUN dnf install -y git python3 python3-jinja2 python3-requests && \
    git clone https://github.com/sio/cirrus-run.git /src && \
    cd /src && \
    git reset --hard b60e45c940e705cfc9d60e35c053f028f0a881b4 && \
    python3 setup.py build && \
    python3 setup.py test && \
    python3 setup.py install --prefix /usr && \
    cd / && \
    rm -rf /src
