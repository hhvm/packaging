# HHVM RPM Spec file
# 
# Helpful Commands
#
# rpmlint hhvm.spec             Lint check on Spec file
# yum-builddep hhvm.spec        Download all dependencies needed to build app
# rpmbuild -bb hhvm.spec        Build binary rpm

Name: hhvm
Version: 3.0.1
Release: 1%{?dist}
License: PHP and Zend and BSD
URL: http://www.hhvm.com/
Summary: HHVM virtual machine, runtime, and JIT for the PHP language
Provides: hhvm
Source0: %{name}-%{version}.tar.bz2
Source1: php.ini
Source2: hhvm.service
Source3: server.hdf
Source4: config.hdf
Source5: static.mime-types.hdf
Source6: THIRD_PARTY
Source7: PHP
Source8: ZEND
Source9: curl
Source10: libafdt
Source11: libglog
Source12: libmbfl
Source13: lz4
Source14: sqlite3
Source15: timelib

BuildRoot: %{_tmppath}/%{name}-%{version}
BuildArch: x86_64
BuildRequires: autoconf
BuildRequires: automake
BuildRequires: make
BuildRequires: cmake
BuildRequires: libtool
BuildRequires: cpp
BuildRequires: gcc-c++
BuildRequires: git
BuildRequires: binutils-devel
BuildRequires: boost-devel
BuildRequires: bzip2-devel
BuildRequires: curl-devel
BuildRequires: expat-devel
BuildRequires: elfutils-libelf-devel
BuildRequires: gd-devel
BuildRequires: glog-devel
BuildRequires: ImageMagick-devel
BuildRequires: jemalloc-devel
BuildRequires: libc-client-devel
BuildRequires: libcap-devel
BuildRequires: libcurl-devel
BuildRequires: libdwarf-devel
BuildRequires: libedit-devel
BuildRequires: libevent-devel
BuildRequires: libicu-devel
BuildRequires: libmcrypt-devel
BuildRequires: libmemcached-devel
BuildRequires: libxslt-devel
BuildRequires: libxml2-devel
BuildRequires: libyaml-devel
BuildRequires: mysql-devel
BuildRequires: pam-devel
BuildRequires: pcre-devel
BuildRequires: ocaml
BuildRequires: oniguruma-devel
BuildRequires: openldap-devel
BuildRequires: readline-devel
BuildRequires: tbb-devel
BuildRequires: zlib-devel

Requires: boost
Requires: glog 

%description 
PHP is an HTML-embedded scripting language. PHP attempts to make it
easy for developers to write dynamically generated web pages. PHP also
offers built-in database integration for several commercial and
non-commercial database management systems, so writing a
database-enabled webpage with PHP is fairly simple. The most common
use of PHP coding is probably as a replacement for CGI scripts.

%prep
%setup -q -n %{name}-%{version}

%build 
export CMAKE_PREFIX_PATH=$RPM_BUILD_ROOT%{_prefix}
cmake . -DCMAKE_INSTALL_PREFIX=$RPM_BUILD_ROOT%{_prefix}
make

%install
make install

# Install Config files in /etc/hhvm
%{__mkdir} -p $RPM_BUILD_ROOT%{_sysconfdir}/hhvm
%{__cp} %{SOURCE1} $RPM_BUILD_ROOT%{_sysconfdir}/hhvm
%{__cp} %{SOURCE3} $RPM_BUILD_ROOT%{_sysconfdir}/hhvm
%{__cp} %{SOURCE4} $RPM_BUILD_ROOT%{_sysconfdir}/hhvm

# Setup service script for systemd
%{__mkdir} -p $RPM_BUILD_ROOT%{_prefix}/lib/systemd/system
%{__cp} %{SOURCE2} $RPM_BUILD_ROOT%{_prefix}/lib/systemd/system

# Setup Static types
%{__mkdir} -p $RPM_BUILD_ROOT%{_datadir}/hhvm/hdf
%{__cp} %{SOURCE5} $RPM_BUILD_ROOT%{_datadir}/hhvm/hdf/static.mime-types.hdf

# Setup Logging
%{__mkdir} -p $RPM_BUILD_ROOT%{_localstatedir}/log/hhvm
# Setup Location for pid file
%{__mkdir} -p $RPM_BUILD_ROOT%{_localstatedir}/run/hhvm

# Setup Licenses
%{__mkdir} -p $RPM_BUILD_ROOT%{_datadir}/hhvm/LICENSE

%{__cp} %{SOURCE6} $RPM_BUILD_ROOT%{_datadir}/hhvm/
%{__cp} %{SOURCE7} $RPM_BUILD_ROOT%{_datadir}/hhvm/LICENSE
%{__cp} %{SOURCE8} $RPM_BUILD_ROOT%{_datadir}/hhvm/LICENSE
%{__cp} %{SOURCE9} $RPM_BUILD_ROOT%{_datadir}/hhvm/LICENSE
%{__cp} %{SOURCE10} $RPM_BUILD_ROOT%{_datadir}/hhvm/LICENSE
%{__cp} %{SOURCE11} $RPM_BUILD_ROOT%{_datadir}/hhvm/LICENSE
%{__cp} %{SOURCE12} $RPM_BUILD_ROOT%{_datadir}/hhvm/LICENSE
%{__cp} %{SOURCE13} $RPM_BUILD_ROOT%{_datadir}/hhvm/LICENSE
%{__cp} %{SOURCE14} $RPM_BUILD_ROOT%{_datadir}/hhvm/LICENSE
%{__cp} %{SOURCE15} $RPM_BUILD_ROOT%{_datadir}/hhvm/LICENSE

%pre
/usr/sbin/useradd -c "www-data" -d /var/www -s /sbin/nologin -r www-data 2>/dev/null || :

%files
%config /etc/hhvm/config.hdf
%config /etc/hhvm/php.ini
%config /etc/hhvm/server.hdf
/usr/lib/systemd/system/hhvm.service
/usr/bin/hhvm
/usr/bin/hphpize
/usr/include/zipconf.h
/usr/include/zip.h
/usr/lib/libzip.a
/usr/lib/libzip.so
/usr/share/hhvm/LICENSE
/usr/share/hhvm/LICENSE/PHP
/usr/share/hhvm/LICENSE/ZEND
/usr/share/hhvm/LICENSE/curl
/usr/share/hhvm/LICENSE/libafdt
/usr/share/hhvm/LICENSE/libglog
/usr/share/hhvm/LICENSE/libmbfl
/usr/share/hhvm/LICENSE/lz4
/usr/share/hhvm/LICENSE/sqlite3
/usr/share/hhvm/LICENSE/timelib
/usr/share/hhvm/THIRD_PARTY
/usr/share/hhvm/hdf/static.mime-types.hdf
/var/log/hhvm
/var/run/hhvm
%attr(775, www-data, www-data) /var/run/hhvm/
%attr(775, www-data, www-data) /var/log/hhvm/

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%changelog
* Sun Jun 29 2014 <jete.okeeffe AT gmail> 3.0.1
 - Release 3.0.1
 - Adding systemd service script
