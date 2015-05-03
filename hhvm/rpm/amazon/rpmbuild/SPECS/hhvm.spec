%define debug_package %{nil}
%global owner facebook
%global project hhvm
%global package_version 1

Name: hhvm
Version: 3.6.2
Summary: HHVM is a new open-source virtual machine designed for executing programs written in PHP. HHVM uses a just-in-time (JIT) compilation approach to achieve superior performance while maintaining the flexibility that PHP developers are accustomed to. http://hhvm.com
Release: %{package_version}%{?dist}
License: GPL
Group: Development/Compilers
Provides: hiphop-php
Packager: Ilya Ivanov <burner1024 @ github>
Url: https://github.com/%{owner}/%{project}
Source0: https://github.com/%{owner}/%{project}/archive/%{project}-%{version}.tar.gz
Source1: hhvm-init
Source2: hhvm-sysconfig
Source3: hhvm-server.ini
Source4: hhvm-static.mime-types.hdf
Patch0: fix-webscalesql_new-b68835746159231ccd8a46c05db572f1be906748.patch
BuildRoot: %{_tmppath}/build-root-%{name}-%{version}
BuildArch: x86_64
BuildRequires: binutils,binutils-devel
BuildRequires: boost-devel >= 1.50
#BuildRequires: cmake >= 3
BuildRequires: curl-devel >= 7.29.0
BuildRequires: elfutils-libelf-devel
BuildRequires: expat-devel
BuildRequires: gd-devel
BuildRequires: git,perl,flex,bison
BuildRequires: glog-devel >= 0.3.2
BuildRequires: gmp-devel
BuildRequires: ImageMagick-devel >= 6.7.8.9
BuildRequires: fastlz-devel
BuildRequires: libcap-devel
BuildRequires: libdwarf-devel
BuildRequires: libedit-devel
BuildRequires: libevent-devel >= 1.4.14
BuildRequires: libicu >= 4.2
BuildRequires: libmcrypt-devel
BuildRequires: libmemcached-devel >= 1.0.8
BuildRequires: libvpx-devel
BuildRequires: libxml2-devel
BuildRequires: libxslt-devel >= 1.1.28
BuildRequires: libyaml-devel
BuildRequires: lz4-devel
BuildRequires: mysql-devel
BuildRequires: oniguruma-devel
BuildRequires: openldap-devel
BuildRequires: openssl-devel
BuildRequires: pcre-devel
BuildRequires: readline-devel
BuildRequires: tbb-devel >= 4
BuildRequires: unixODBC-devel >= 2.2.14-12
BuildRequires: zlib-devel

Requires: boost >= 1.50.0
Requires: curl >= 7.29.0
Requires: expat >= 2.0.1
Requires: gcc >= 4.6.0 ,gcc-c++,make
Requires: gd >= 2.0.35
Requires: glog >= 0.3.2
Requires: libcap
Requires: libdwarf >= 20130207
Requires: libevent >= 1.4.14
Requires: libicu >= 4.2
Requires: libmcrypt >= 2.5.8-9
Requires: libmemcached >= 1.0.8
Requires: mysql
Requires: oniguruma >= 5.9
Requires: openssl
Requires: pcre
Requires: tbb >= 4
Requires: unixODBC >= 2.2.14-12
Requires: zlib

%description
HipHop for PHP is an open source project developed by Facebook. HipHop offers a PHP execution engine called the "HipHop Virtual Machine" (HHVM) which uses a just-in-time compilation approach to achieve superior performance. To date, Facebook has achieved more than a 6x reduction in CPU utilization for the site using HipHop as compared with Zend PHP.

%prep
%setup -qn %{name}-%{version}
%patch0 -p1

%build
export USE_HHVM=1
export HPHP_HOME=`pwd`
export HPHP_LIB=`pwd`/bin
cmake -DMYSQL_UNIX_SOCK_ADDR=/var/lib/mysql/mysql.sock .
make

%install
export QA_RPATHS=$[ 0x0001|0x0010 ]

ls > filelist
mkdir -p $RPM_BUILD_ROOT/%{_libdir}/hiphop-php
mv `cat filelist` $RPM_BUILD_ROOT/%{_libdir}/hiphop-php/
mkdir -p $RPM_BUILD_ROOT/%{_bindir}
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/hhvm
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/init.d
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/sysconfig
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/profile.d
mkdir -p $RPM_BUILD_ROOT/%{_datadir}/share/hhvm/hdf/
mkdir -p $RPM_BUILD_ROOT/var/log/hhvm/
mkdir -p $RPM_BUILD_ROOT/usr/share/hhvm/hdf/

# Copy the init script
%{__install} -m 755 -p %{SOURCE1} \
	$RPM_BUILD_ROOT/%{_sysconfdir}/init.d/hhvm
# Copy the sysconfig hhvm
%{__install} -m 644 -p %{SOURCE2} \
	$RPM_BUILD_ROOT/%{_sysconfdir}/sysconfig/hhvm
# Copy the server.ini
%{__install} -m 644 -p %{SOURCE3} \
	$RPM_BUILD_ROOT/%{_sysconfdir}/hhvm/server.ini
# Copy the static.mime-types.hdf
%{__install} -m 644 -p %{SOURCE4} \
	$RPM_BUILD_ROOT/usr/share/hhvm/hdf/static.mime-types.hdf
# Copy the actual binary
%{__install} -m 755 -p $RPM_BUILD_ROOT/%{_libdir}/hiphop-php/hphp/hhvm/hhvm \
	$RPM_BUILD_ROOT/%{_bindir}/hhvm
echo "export USE_HHVM=1" > $RPM_BUILD_ROOT/%{_sysconfdir}/profile.d/hphp.sh
echo "export HPHP_HOME=%{_libdir}/hiphop-php" >> $RPM_BUILD_ROOT/%{_sysconfdir}/profile.d/hphp.sh
echo "export HPHP_LIB=%{_libdir}/hiphop-php/bin" >> /$RPM_BUILD_ROOT/%{_sysconfdir}/profile.d/hphp.sh
echo "export HHVM_LIB_PATH=%{_libdir}/hiphop-php/bin" >> $RPM_BUILD_ROOT/%{_sysconfdir}/profile.d/hphp.sh
rm -rf $RPM_BUILD_ROOT/%{_libdir}

%files
%defattr(-,root,root,-)
/etc/init.d/hhvm
/etc/hhvm/server.ini
/etc/profile.d/hphp.sh
/etc/sysconfig/hhvm
/usr/bin/hhvm
/usr/share/hhvm/hdf/static.mime-types.hdf
/var/log/hhvm/


%changelog
* Sun May 3 2015 Ilya Ivanov <burner1024 @ github>
 - Use HHVM releases instead of current git branches
 - Build release 3.6.2
 - Add mysql socket arg to cmake, so it doesn't fail
 - Bump required cmake version to 3 (http://www.cmake.org/files/v3.2/cmake-3.2.2-Linux-x86_64.tar.gz is used currently)
 - Apply websqlclient patch (https://github.com/facebook/hhvm/issues/5100, https://gerrit.wikimedia.org/r/#/c/200513/1/debian/patches/fix-webscalesql.patch)
 - Add a few libraries to build requirements, so that support is built-in

* Fri Sep 19 2014 Ilya Ivanov <burner1024 @ github>
 - Update to commit 46e69b6c2402a19478f263336a6cb35057f40a19
 - Move repo.central.path to /tmp by default to avoid denied file permissions

* Thu Sep 11 2014 Ilya Ivanov <burner1024 @ github>
 - Adapt for Amazon Linux
 - Release 3.3.0

* Thu Sep 11 2014 BogusDateBot
- Eliminated rpmbuild "bogus date" warnings due to inconsistent weekday,
  by assuming the date is correct and changing the weekday.
  Fri Mar 16 2013 --> Fri Mar 15 2013 or Sat Mar 16 2013 or Fri Mar 22 2013 or ....
  Fri Mar 24 2013 --> Fri Mar 22 2013 or Sun Mar 24 2013 or Fri Mar 29 2013 or ....
  Sun May 07 2013 --> Sun May 05 2013 or Tue May 07 2013 or Sun May 12 2013 or ....
  Sun May 17 2013 --> Sun May 12 2013 or Fri May 17 2013 or Sun May 19 2013 or ....
  Sun May 21 2013 --> Sun May 19 2013 or Tue May 21 2013 or Sun May 26 2013 or ....
  Sat Dec 15 2013 --> Sat Dec 14 2013 or Sun Dec 15 2013 or Sat Dec 21 2013 or ....
  Sun Jan 04 2014 --> Sun Dec 29 2013 or Sat Jan 04 2014 or Sun Jan 05 2014 or ....

* Fri Mar 7 2014 Naresh <cyan_00391 AT yahoo> 2.4.2-1
 - Release 2.4.2

* Tue Feb 4 2014 Naresh <cyan_00391 AT yahoo> 2.4.0-1
 - Release 2.4.0

* Sun Jan 19 2014 Naresh <cyan_00391 AT yahoo> 2.3.3-1
 - Release 2.3.3

* Sat Jan 04 2014 Naresh <cyan_00391 AT yahoo> 2.3.2-3
  Sun Jan 04 2014 --> Sun Dec 29 2013 or Sat Jan 04 2014 or Sun Jan 05 2014 or ....
  - charset support in Mysql DSN

* Mon Dec 30 2013 Naresh <cyan_00391 AT yahoo> 2.3.2
  - 2.3.2 release

* Wed Dec 18 2013 Naresh <cyan_00391 AT yahoo> 2.3.1
  - 2.3.1 release

* Sun Dec 15 2013 Naresh <cyan_00391 AT yahoo> 2.3.0
  Sat Dec 15 2013 --> Sat Dec 14 2013 or Sun Dec 15 2013 or Sat Dec 21 2013 or ....
  - 2.3.0 release

* Sat Oct 19 2013 Naresh <cyan_00391 AT yahoo> 2.2.0
  - 2.2.0 release

* Thu Sep 5 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.210.2-1
  - "Kimchi" Release
  - Implement CachingIterator
  - Implement RecursiveCachingIterator
  - Generalized heuristic for choosing when to inline in the jit
  - Imported calendar extension
  - Use gcc-4.8.1 by default
  - Improve hhvm commandline parsing logic
  - Fix register_shutdown in session_set_save_handler to match PHP 5.4
  - Add "native" functions for use in Systemlib
  - PHP extension source-compatitblility layer
  - Fix ArrayIterator constructor PHP compatibility
  - Enable building against libmemcached 1.0.8
  - Debugger: $_ not cleared but still printed after exception
  - Fix clone of SplPriorityQueue
  - Debugger: Fix bugs when multiple threads hit the same breakpoint
  - Fix several namespace bugs
  - Several PHP compatibility fixes for ArrayObject and ArrayIterator
  - Fix list assignment with collection literals
  - support "tuple(...)" in initializer expressions
  - HHVM should compile with libmemcached 1.0.9+
  - Support "(new Vector {..})->method()" style syntax
  - use trigger_error in PHP for Redis user errors
  - multiple simplexml fixes
  - fixed serialize/unserialize for SplObjectStorage
  - Implement ReflectionParameter::IsCallable()

* Sun Sep 1 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.210.1-1
- Build High performance version as of sep-1-2013 
- Commit https://github.com/facebook/hiphop-php/commit/ed8774975e0c017b8baf09d1547d769b26c5f278

* Fri Jul 12 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.210-0
- 2.1.0 Final release
- Build with jemalloc 3.4.0

* Fri Jul 12 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.210-4
- Till 86b00778e384caa8c22b2fb2917182bff58475df
- Build with jemalloc 3.4.0

* Tue May 21 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.210-3
  Sun May 21 2013 --> Sun May 19 2013 or Tue May 21 2013 or Sun May 26 2013 or ....
- Till be9f36d3bcaaedc295b52c0232fcc9c8d7ef8e95

* Fri May 17 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.210-2
  Sun May 17 2013 --> Sun May 12 2013 or Fri May 17 2013 or Sun May 19 2013 or ....
- Git 2.1.0-dev
- with REQUEST_TIME_FLOAT patch

* Fri May 17 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.210-1
  Sun May 17 2013 --> Sun May 12 2013 or Fri May 17 2013 or Sun May 19 2013 or ....
- Git 2.1.0-dev

* Tue May 07 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.202-1
  Sun May 07 2013 --> Sun May 05 2013 or Tue May 07 2013 or Sun May 12 2013 or ....
- Git 2.0.2
- No jemalloc patch

* Sun Apr 07 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.0-3
- Build from latest git 07-Apr-2013
- Disable perf counters issue #672 (enable again)
- Disable Jemalloc 32-bit allocation to fix systemlib.php error #724
- Change version to 2.1.0 (drop date time specs in version)

* Sun Apr 07 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.0-2
- Build from latest git 07-Apr-2013
- Disable perf counters issue #672
- Disable Jemalloc 32-bit allocation to fix systemlib.php error #724
- Change version to 2.1.0 (drop date time specs in version)

* Sun Apr 07 2013 Naresh Kumar <cyan_00391 AT yahoo> 2.1.0-1
- Build from latest git 07-Apr-2013
- Change version to 2.1.0 (drop date time specs in version)

* Sun Mar 24 2013 Naresh Kumar <cyan_00391 AT yahoo>
  Fri Mar 24 2013 --> Fri Mar 22 2013 or Sun Mar 24 2013 or Fri Mar 29 2013 or ....
- Build from latest git 30-Mar-2013, IST 03:00 PM
- Disable jemalloc 32 bit allocation

* Sun Mar 24 2013 Naresh Kumar <cyan_00391 AT yahoo>
  Fri Mar 24 2013 --> Fri Mar 22 2013 or Sun Mar 24 2013 or Fri Mar 29 2013 or ....
- Build from latest git 24-Mar-2013, IST 08:00 AM

* Sat Mar 16 2013 Naresh Kumar <cyan_00391 AT yahoo>
  Fri Mar 16 2013 --> Fri Mar 15 2013 or Sat Mar 16 2013 or Fri Mar 22 2013 or ....
- Build from latest git 16-Mar-2013, IST 11:00 AM

* Fri Jan 06 2012 Naresh Kumar <cyan_00391 AT yahoo>
- EL6.2 changes
- added RPATH values
- added %postun section
