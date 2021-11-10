FROM docker.io/library/alpine:3.14

RUN apk update && \
    apk upgrade && \
    apk add \
        ca-certificates \
        gcc \
        git \
        glib-dev \
        gtk-doc \
        pkgconf

ENV LANG "en_US.UTF-8"