FROM debian:wheezy
ADD ./bin /opt/hhvm-docker-bin
RUN \
  /opt/hhvm-docker-bin/install-essential-debs && \
  /opt/hhvm-docker-bin/build-gcc && \
  /opt/hhvm-docker-bin/build-glog && \
  /opt/hhvm-docker-bin/build-jemalloc && \
  rm -rf /tmp/*
