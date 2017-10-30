FROM debian:wheezy
ADD ./bin /opt/hhvm-docker-bin
RUN \
  /opt/hhvm-docker-bin/install-essential-debs && \
  /opt/hhvm-docker-bin/build-gcc-5
