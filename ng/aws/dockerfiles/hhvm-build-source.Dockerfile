FROM ubuntu:xenial
ADD . /opt/hhvm-packaging
ENV TZ UTC
ENV DEBIAN_FRONTEND noninteractive
RUN \
  apt-get update -y && \
  apt-get install -y curl wget git awscli && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists
CMD /opt/hhvm-packaging/aws/bin/make-source-tarball
