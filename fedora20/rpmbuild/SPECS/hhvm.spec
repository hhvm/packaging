Name: hhvm
Version: 2.3.2
Release: 1%{?dist}
License: PHP and Zend and BSD
URL: http://www.hhvm.com/
Summary: HHVM virtual machine, runtime, and JIT for the PHP language

%description 
PHP is an HTML-embedded scripting language. PHP attempts to make it
easy for developers to write dynamically generated web pages. PHP also
offers built-in database integration for several commercial and
non-commercial database management systems, so writing a
database-enabled webpage with PHP is fairly simple. The most common
use of PHP coding is probably as a replacement for CGI scripts.

%prep
%build

%install
rsync -av ~/packaging/fedora20/root/ %{buildroot}

%pre
/usr/sbin/useradd -c "www-data" -d /var/www -s /sbin/nologin -r www-data 2>/dev/null || :

%files
/etc/hhvm/config.hdf
/etc/hhvm/php.ini
/etc/hhvm/server.hdf
/etc/init.d/hhvm
/usr/bin/hhvm
/usr/lib/hhvm/libevent-1.4.so.2
/usr/lib/hhvm/libglog.so.0
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
/var/www
%attr(775, www-data, www-data) /var/run/hhvm/
%attr(775, www-data, www-data) /var/log/hhvm/

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
