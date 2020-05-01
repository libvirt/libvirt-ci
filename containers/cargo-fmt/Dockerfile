FROM rust:1.43

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --no-install-recommends -y \
            diffstat && \
    apt-get autoclean -y && \
    rustup component add rustfmt

COPY cargo-fmt.sh /cargo-fmt
