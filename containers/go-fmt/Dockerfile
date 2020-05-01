FROM golang:1.14

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --no-install-recommends -y \
            diffstat && \
    apt-get autoclean -y

COPY go-fmt.sh /go-fmt
