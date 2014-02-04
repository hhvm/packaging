## To run this on generic sl6, you need to install 'devtoolset-2-toolchain' (or the whole
## devtoolset-2 package), as described here:
## http://linux.web.cern.ch/linux/devtoolset/#install
## After installing devtoolset-2-toolchain via yum (which provides gcc 4.8), enter into the
## new environment containing gcc 4.8 with `scl enable devtoolset-2 bash`.
## Then, you need to package up HHVM into a tar.gz in SOURCES/ with the proper version number,
## and then update the version number below (or just amend this specfile to pull the head of HHVM
## into _builddir, or something)
## Then, finally, you can build this rpm

## NOTE: this sets the number of workers used by make... set this low if theres not alot of memory
## otherwise make likes to fail/segfault
%define num_make_workers 8

Name: hhvm
## changeme!
Version: 2.4.0
Release: 2%{?dist}
License: PHP and Zend and BSD
URL: http://www.hhvm.com/
Summary: HHVM virtual machine, runtime, and JIT for the PHP language
SOURCE0 : %{name}-%{version}.tar.gz
SOURCE1: libevent-1.4.14b-patched.tar.gz
SOURCE2: google-glog_r139.tar.gz
SOURCE3: jemalloc-3.0.0.tar.bz2
SOURCE4: libdwarf_a4a854.tar.gz
SOURCE5: curl_6c014e.tar.gz
SOURCE6: libmemcached-1.0.17.tar.gz
SOURCE7: boost_1_55_0.tar.gz
SOURCE8: tbb40_20120613oss_src.tgz

Requires: libpng >= 1.2.49
Requires: audit-libs >= 2.2
Requires: bzip2-libs >= 1.0.5
Requires: cyrus-sasl-lib >= 2.1.23
Requires: elfutils-libelf >= 0.152
Requires: expat >= 2.0.1
Requires: freetype >= 2.3.11
Requires: glibc >= 2.12
Requires: keyutils-libs >= 1.4
Requires: krb5-libs >= 1.10.3
Requires: libattr >= 2.4.44
Requires: libc-client
Requires: libcap >= 2.16
Requires: libcom_err >= 1.41
Requires: libicu >= 4.2.1
Requires: libjpeg
Requires: libjpeg-turbo >= 1.2.1
Requires: libselinux >= 2.0.94
Requires: libxml2 >= 2.7.6
Requires: ncurses-libs >= 5.7
Requires: nspr >= 4.10.2
Requires: nss >= 3.14
Requires: nss-softokn-freebl >= 3.14.3
Requires: nss-util >= 3.14
Requires: oniguruma >= 5.9.1
Requires: openldap >= 2.4.23
Requires: openssl >= 1.0
Requires: pam >= 1.1.1
Requires: pcre >= 7.8
Requires: readline >= 6.0
Requires: zlib >= 1.2.3
## the below can be swapped out for mysql-devel
Requires: Percona-Server-shared-55 >= 5.5
Requires: libgcc >= 4.4.7
Requires: libstdc++ >= 4.4.7
Requires: libmcrypt >= 2.5.8

BuildRequires: chrpath
BuildRequires: mpfr
BuildRequires: glibc-devel >= 2.12
BuildRequires: policycoreutils-python
BuildRequires: libgfortran
BuildRequires: libmcrypt-devel >= 2.5.8
BuildRequires: cmake >= 2.8.12
BuildRequires: git
BuildRequires: svn
BuildRequires: make
BuildRequires: autoconf
BuildRequires: automake
BuildRequires: libtool
BuildRequires: patch
BuildRequires: memcached
BuildRequires: pcre-devel >= 7.8
BuildRequires: gd-devel
BuildRequires: libxml2-devel >= 2.7.6
BuildRequires: expat-devel >= 2.0.1
BuildRequires: libicu-devel >= 4.2.1
BuildRequires: bzip2-devel >= 1.0.5
BuildRequires: oniguruma-devel >= 5.9.1
BuildRequires: openldap-devel >= 2.4.23
BuildRequires: readline-devel >= 6.0
BuildRequires: libc-client-devel
BuildRequires: libcap-devel >= 2.16
BuildRequires: binutils-devel
BuildRequires: pam-devel >= 1.1.1
BuildRequires: elfutils-libelf-devel >= 0.152
BuildRequires: rpm-build
BuildRequires: flex
BuildRequires: bison
BuildRequires: openssl-devel >= 1.0
## the below can be swapped out for mysql-devel
BuildRequires: Percona-Server-devel-55 >= 5.5

#### devtoolset and related packages
BuildRequires: gcc >= 4.8.1
BuildRequires: devtoolset-2-toolchain

Provides: hhvm = %{version}

%description
PHP is an HTML-embedded scripting language. PHP attempts to make it
easy for developers to write dynamically generated web pages. PHP also
offers built-in database integration for several commercial and
non-commercial database management systems, so writing a
database-enabled webpage with PHP is fairly simple. The most common
use of PHP coding is probably as a replacement for CGI scripts.

%prep

%build
## temp_install_dir is the temporary location where we will place all non-standard dependencies
## of HHVM
rm -rf %{_builddir}/temp_install_dir
mkdir -p %{_builddir}/temp_install_dir

#========= LIBEVENT =========
tar -zxf %{SOURCE1}
cd libevent
./autogen.sh
./configure --prefix=%{_builddir}/temp_install_dir
make -j %{num_make_workers}
make install
cd ..

#======== google glog =============
tar -zxf %{SOURCE2}
cd google-glog
./configure --prefix=%{_builddir}/temp_install_dir
make -j %{num_make_workers}
make install
cd ..

#================= jemalloc ==================
tar -xjf %{SOURCE3}
cd jemalloc-3.0.0
./configure --prefix=%{_builddir}/temp_install_dir
make -j %{num_make_workers}
make install
cd ..

#================ lib dwarf ===================
tar -xzf %{SOURCE4}
cd libdwarf/libdwarf
./configure
make -j %{num_make_workers}
cp libdwarf.h %{_builddir}/temp_install_dir/include/
cp dwarf.h %{_builddir}/temp_install_dir/include/
cp libdwarf.a %{_builddir}/temp_install_dir/lib/
cd ../..

#============ LIBcurl ===========
tar -xzf %{SOURCE5}
cd curl
./buildconf
./configure --prefix=%{_builddir}/temp_install_dir
make -j %{num_make_workers}
make install
cd ..

#============= lib memcached ==============
tar -xzf %{SOURCE6}
cd libmemcached-1.0.17
./configure --prefix=%{_builddir}/temp_install_dir
sed -i s/-fsanitize=address//g Makefile
sed -i s/-fsanitize=thread//g Makefile
make -j %{num_make_workers}
make install
cd ..

#======================= BOOST =========================
tar -xzf %{SOURCE7}
cd boost_1_55_0
echo "using gcc : : `which gcc` ;" >> tools/build/v2/user-config.jam
./bootstrap.sh --prefix=%{_builddir}/temp_install_dir --libdir=%{_builddir}/temp_install_dir/lib

## Boost always fails to update everything, just ignore it. Boost, you are the worst
set +e
./bjam -j%{num_make_workers} --layout=system install
set -e
cd ..

#============== thread building blocks ==============
tar -xzf %{SOURCE8}
cd tbb40_20120613oss
make -j %{num_make_workers}
mkdir -p %{_builddir}/temp_install_dir/include/serial
cp -a include/serial/* %{_builddir}/temp_install_dir/include/serial/
mkdir -p %{_builddir}/temp_install_dir/include/tbb
cp -a include/tbb/* %{_builddir}/temp_install_dir/include/tbb/
cp build/linux_intel64_gcc_cc4.8.1_libc2.12_kernel2.6.32_release/libtbb.so.2 %{_builddir}/temp_install_dir/lib/
ln -s %{_builddir}/temp_install_dir/lib/libtbb.so.2 %{_builddir}/temp_install_dir/lib/libtbb.so
cd ..

######## ========== BUILD HHVM!!! =========== ##########
tar -xzf %{SOURCE0}
cd hhvm

## for debugging and static linking of boost
sed -i '1s/^/SET(Boost_DEBUG ON)\n/' CMake/FindBoost.cmake
sed -i '1s/^/SET(Boost_USE_STATIC_LIBS ON)\n/' CMake/FindBoost.cmake

rm CMakeCache.txt && rm -rf CMakeFiles/ && rm cmake_install.cmake
BOOST_LIBRARYDIR=%{_builddir}/temp_install_dir/include/boost/ CMAKE_INCLUDE_PATH=%{_builddir}/temp_install_dir/include/ CMAKE_LIBRARY_PATH="%{_builddir}/temp_install_dir/lib/" HPHP_HOME=`pwd` CC=`which gcc` CXX=`which g++` cmake .
make -j %{num_make_workers}

## move over the hhvm binary!
cp hphp/hhvm/hhvm %{_builddir}/temp_install_dir/bin/

%install
rm -rf %{buildroot}/usr/lib/hhvm/
mkdir -p %{buildroot}/usr/lib/hhvm/
rm -rf %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/bin

cp -d %{_builddir}/temp_install_dir/lib/libevent.so %{buildroot}/usr/lib/hhvm/
cp -d %{_builddir}/temp_install_dir/lib/libevent-1.4.so.2 %{buildroot}/usr/lib/hhvm/
cp -d %{_builddir}/temp_install_dir/lib/libevent-1.4.so.2.2.0 %{buildroot}/usr/lib/hhvm/

cp -d %{_builddir}/temp_install_dir/lib/libglog.so %{buildroot}/usr/lib/hhvm/
cp -d %{_builddir}/temp_install_dir/lib/libglog.so.0 %{buildroot}/usr/lib/hhvm/
cp -d %{_builddir}/temp_install_dir/lib/libglog.so.0.0.0 %{buildroot}/usr/lib/hhvm/

cp -d %{_builddir}/temp_install_dir/lib/libjemalloc.so %{buildroot}/usr/lib/hhvm/
cp -d %{_builddir}/temp_install_dir/lib/libjemalloc.so.1 %{buildroot}/usr/lib/hhvm/

cp %{_builddir}/temp_install_dir/lib/libdwarf.a %{buildroot}/usr/lib/hhvm/

cp -d %{_builddir}/temp_install_dir/lib/libcurl.so %{buildroot}/usr/lib/hhvm
cp -d %{_builddir}/temp_install_dir/lib/libcurl.so.4 %{buildroot}/usr/lib/hhvm
cp -d %{_builddir}/temp_install_dir/lib/libcurl.so.4.3.0 %{buildroot}/usr/lib/hhvm

cp -d %{_builddir}/temp_install_dir/lib/libmemcached.so %{buildroot}/usr/lib/hhvm
cp -d %{_builddir}/temp_install_dir/lib/libmemcached.so.11 %{buildroot}/usr/lib/hhvm
cp -d %{_builddir}/temp_install_dir/lib/libmemcached.so.11.0.0 %{buildroot}/usr/lib/hhvm

cp -d %{_builddir}/temp_install_dir/lib/libtbb.so.2 %{buildroot}/usr/lib/hhvm/
cp -d %{_builddir}/temp_install_dir/lib/libtbb.so %{buildroot}/usr/lib/hhvm/

### copy over hhvm!
cp -d %{_builddir}/temp_install_dir/bin/hhvm %{buildroot}/usr/bin/

### finally, fix up the RPATH of the hhvm binary to always look in /usr/lib/hhvm
### for shared libs
chrpath -r '/usr/lib/hhvm' %{buildroot}/usr/bin/hhvm

%files
/usr/bin/hhvm
/usr/lib/hhvm/*
### TODO(ptarjan or jmarrama): package the LICENSES too?
#/usr/share/hhvm/LICENSE
#/usr/share/hhvm/LICENSE/PHP
#/usr/share/hhvm/LICENSE/ZEND
#/usr/share/hhvm/LICENSE/curl
#/usr/share/hhvm/LICENSE/libafdt
#/usr/share/hhvm/LICENSE/libglog
#/usr/share/hhvm/LICENSE/libmbfl
#/usr/share/hhvm/LICENSE/lz4
#/usr/share/hhvm/LICENSE/sqlite3
#/usr/share/hhvm/LICENSE/timelib
#/usr/share/hhvm/THIRD_PARTY
#/usr/share/hhvm/hdf/static.mime-types.hdf
#/var/log/hhvm
#/var/run/hhvm
#%attr(775, www-data, www-data) /var/run/hhvm/
#%attr(775, www-data, www-data) /var/log/hhvm/

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
