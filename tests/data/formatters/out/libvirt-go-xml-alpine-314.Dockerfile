FROM docker.io/library/alpine:3.14

RUN apk update && \
    apk upgrade && \
    apk add \
        ca-certificates \
        git \
        go && \
    apk list | sort > /packages.txt

ENV LANG "en_US.UTF-8"