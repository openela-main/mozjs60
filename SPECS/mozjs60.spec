%global major 60

# Require libatomic for ppc
%ifarch ppc
%global system_libatomic 1
%endif

# Big endian platforms
%ifarch ppc ppc64 s390 s390x
%global big_endian 1
%endif

Name:           mozjs%{major}
Version:        60.9.0
Release:        4%{?dist}
Summary:        SpiderMonkey JavaScript library

License:        MPLv2.0 and MPLv1.1 and BSD and GPLv2+ and GPLv3+ and LGPLv2+ and AFL and ASL 2.0
URL:            https://developer.mozilla.org/en-US/docs/Mozilla/Projects/SpiderMonkey
Source0:        https://ftp.mozilla.org/pub/firefox/releases/%{version}esr/source/firefox-%{version}esr.source.tar.xz

# Patches from Debian mozjs52_52.3.1-4.debian.tar.xz:
Patch0001:      fix-soname.patch
Patch0002:      copy-headers.patch
Patch0003:      tests-increase-timeout.patch
Patch0008:      Always-use-the-equivalent-year-to-determine-the-time-zone.patch
Patch0009:      icu_sources_data.py-Decouple-from-Mozilla-build-system.patch
Patch0010:      icu_sources_data-Write-command-output-to-our-stderr.patch
Patch0011:      tests-For-tests-that-are-skipped-on-64-bit-mips64-is-also.patch

# Build fixes - https://hg.mozilla.org/mozilla-central/rev/ca36a6c4f8a4a0ddaa033fdbe20836d87bbfb873
Patch12:        emitter.patch
Patch13:        emitter_test.patch
Patch14:        init_patch.patch

# s390x fixes:
# https://salsa.debian.org/gnome-team/mozjs60/blob/debian/master/debian/patches/enddianness.patch
Patch15:        enddianness.patch
# https://salsa.debian.org/gnome-team/mozjs60/blob/debian/master/debian/patches/jsproperty-endian.patch
Patch16:        jsproperty-endian.patch
# https://salsa.debian.org/gnome-team/mozjs60/blob/debian/master/debian/patches/tests-Skip-a-test-on-s390x.patch
Patch17:        tests-Skip-a-test-on-s390x.patch
# https://salsa.debian.org/gnome-team/mozjs60/blob/debian/master/debian/patches/tests-Expect-a-test-to-fail-on-big-endian.patch
Patch18:        tests-Expect-a-test-to-fail-on-big-endian.patch

# Patches from Fedora firefox package:
Patch26:        build-icu-big-endian.patch

# aarch64 fixes for -O2
Patch30:        Save-x28-before-clobbering-it-in-the-regex-compiler.patch
Patch31:        Save-and-restore-non-volatile-x28-on-ARM64-for-generated-unboxed-object-constructor.patch

BuildRequires:  autoconf213
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  perl-devel
BuildRequires:  pkgconfig(libffi)
BuildRequires:  pkgconfig(zlib)
BuildRequires:  python2-devel
BuildRequires:  readline-devel
BuildRequires:  /usr/bin/zip
%if 0%{?system_libatomic}
BuildRequires:  libatomic
%endif

# Firefox does not allow to build with system version of jemalloc
Provides: bundled(jemalloc) = 4.3.1

%description
SpiderMonkey is the code-name for Mozilla Firefox's C++ implementation of
JavaScript. It is intended to be embedded in other applications
that provide host environments for JavaScript.

%package        devel
Summary:        Development files for %{name}
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description    devel
The %{name}-devel package contains libraries and header files for
developing applications that use %{name}.

%prep
%setup -q -n firefox-%{version}/js/src

pushd ../..
%patch0001 -p1
%patch0002 -p1
%patch0003 -p1
%patch0008 -p1
%patch0009 -p1
%patch0010 -p1
%patch0011 -p1

%patch12 -p1
%patch13 -p1
%patch14 -p1

# s390x fixes
%patch15 -p1
%patch16 -p1
%patch17 -p1
%patch18 -p1

# Patch for big endian platforms only
%if 0%{?big_endian}
%patch26 -p1 -b .icu
%endif

# aarch64 -O2 fixes
%ifarch aarch64
%patch30 -p1
%patch31 -p1
%endif

# make sure we don't ever accidentally link against bundled security libs
rm -rf security/
popd

# Remove zlib directory (to be sure using system version)
rm -rf ../../modules/zlib

%build
export CFLAGS="%{optflags}"

export CXXFLAGS="$CFLAGS"
export LINKFLAGS="%{?__global_ldflags}"
export PYTHON="%{__python2}"
# Keep using Python 2 for the build for now
# https://bugzilla.redhat.com/show_bug.cgi?id=1610009
export RHEL_ALLOW_PYTHON2_FOR_BUILD=1

autoconf-2.13
%configure \
  --without-system-icu \
  --enable-posix-nspr-emulation \
  --with-system-zlib \
  --enable-tests \
  --disable-strip \
  --with-intl-api \
  --enable-readline \
  --enable-shared-js \
  --disable-optimize \
  --enable-pie \
  --disable-jemalloc \

%if 0%{?big_endian}
echo "Generate big endian version of config/external/icu/data/icud58l.dat"
pushd ../..
  ./mach python intl/icu_sources_data.py .
  ls -l config/external/icu/data
  rm -f config/external/icu/data/icudt*l.dat
popd
%endif

%make_build

%install
# Keep using Python 2 for the build for now
# https://bugzilla.redhat.com/show_bug.cgi?id=1610009
export RHEL_ALLOW_PYTHON2_FOR_BUILD=1

%make_install

# Fix permissions
chmod -x %{buildroot}%{_libdir}/pkgconfig/*.pc

# Avoid multilib conflicts
case `uname -i` in
  i386 | ppc | s390 | sparc )
    wordsize="32"
    ;;
  x86_64 | ppc64 | s390x | sparc64 )
    wordsize="64"
    ;;
  *)
    wordsize=""
    ;;
esac

if test -n "$wordsize"
then
  mv %{buildroot}%{_includedir}/mozjs-60/js-config.h \
     %{buildroot}%{_includedir}/mozjs-60/js-config-$wordsize.h

  cat >%{buildroot}%{_includedir}/mozjs-60/js-config.h <<EOF
#ifndef JS_CONFIG_H_MULTILIB
#define JS_CONFIG_H_MULTILIB

#include <bits/wordsize.h>

#if __WORDSIZE == 32
# include "js-config-32.h"
#elif __WORDSIZE == 64
# include "js-config-64.h"
#else
# error "unexpected value for __WORDSIZE macro"
#endif

#endif
EOF

fi

# Remove unneeded files
rm %{buildroot}%{_bindir}/js%{major}
rm %{buildroot}%{_bindir}/js%{major}-config
rm %{buildroot}%{_libdir}/libjs_static.ajs

# Rename library and create symlinks, following fix-soname.patch
mv %{buildroot}%{_libdir}/libmozjs-%{major}.so \
   %{buildroot}%{_libdir}/libmozjs-%{major}.so.0.0.0
ln -s libmozjs-%{major}.so.0.0.0 %{buildroot}%{_libdir}/libmozjs-%{major}.so.0
ln -s libmozjs-%{major}.so.0 %{buildroot}%{_libdir}/libmozjs-%{major}.so

%check
# Run SpiderMonkey tests
/usr/bin/python2-for-tests tests/jstests.py -d -s -t 1800 --no-progress ../../js/src/js/src/shell/js \
%ifarch %{ix86} x86_64 %{arm} aarch64 ppc ppc64le s390x
;
%else
|| :
%endif

# Run basic JIT tests
/usr/bin/python2-for-tests jit-test/jit_test.py -s -t 1800 --no-progress ../../js/src/js/src/shell/js basic \
%ifarch %{ix86} x86_64 %{arm} aarch64 ppc ppc64le s390x
;
%else
|| :
%endif

%ldconfig_scriptlets

%files
%doc README.html
%{_libdir}/libmozjs-%{major}.so.0*

%files devel
%{_libdir}/libmozjs-%{major}.so
%{_libdir}/pkgconfig/*.pc
%{_includedir}/mozjs-%{major}/

%changelog
* Mon Feb 17 2020 Kalev Lember <klember@redhat.com> - 60.9.0-4
- Update enddianness.patch with more s390x fixes
- Enable tests on s390x again
- Resolves: #1803824

* Tue Sep 10 2019 Kalev Lember <klember@redhat.com> - 60.9.0-3
- Fix multilib conflicts in js-config.h

* Sat Sep 07 2019 Kalev Lember <klember@redhat.com> - 60.9.0-2
- Backport patches for s390x support
- Resolves: #1746889

* Tue Sep 03 2019 Kalev Lember <klember@redhat.com> - 60.9.0-1
- Update to 60.9.0

* Wed May 29 2019 Kalev Lember <klember@redhat.com> - 60.7.0-2
- Enable gating

* Tue May 21 2019 Kalev Lember <klember@redhat.com> - 60.7.0-1
- Update to 60.7.0

* Mon Apr 15 2019 Frantisek Zatloukal <fzatlouk@redhat.com> - 60.6.1-2
- Backport two Firefox 61 patches and allow compiler optimizations on aarch64

* Sun Apr 14 2019 Frantisek Zatloukal <fzatlouk@redhat.com> - 60.6.1-1
- Update to 60.6.1

* Thu Feb 21 2019 Frantisek Zatloukal <fzatlouk@redhat.com> - 60.4.0-5
- Re-enable null pointer gcc optimization

* Sun Feb 17 2019 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 60.4.0-4
- Rebuild for readline 8.0

* Thu Feb 14 2019 Frantisek Zatloukal <fzatlouk@redhat.com> - 60.4.0-3
- Build aarch64 with -O0 because of rhbz#1676292

* Fri Feb 01 2019 Fedora Release Engineering <releng@fedoraproject.org> - 60.4.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_30_Mass_Rebuild

* Wed Jan 02 2019 Frantisek Zatloukal <fzatlouk@redhat.com> - 60.4.0-1
- Update to 60.4.0

* Mon Nov 12 2018 Kalev Lember <klember@redhat.com> - 60.3.0-1
- Update to 60.3.0

* Thu Oct 04 2018 Kalev Lember <klember@redhat.com> - 60.2.2-1
- Update to 60.2.2

* Fri Sep 28 2018 Kalev Lember <klember@redhat.com> - 60.2.1-1
- Update to 60.2.1

* Tue Sep 11 2018 Kalev Lember <klember@redhat.com> - 60.2.0-1
- Update to 60.2.0

* Tue Sep 04 2018 Frantisek Zatloukal <fzatlouk@redhat.com> - 60.1.0-1
- Update to 60.1.0

* Wed Jul 25 2018 Kalev Lember <klember@redhat.com> - 52.9.0-1
- Update to 52.9.0

* Fri Jul 13 2018 Fedora Release Engineering <releng@fedoraproject.org> - 52.8.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Mon Jun 11 2018 Ray Strode <rstrode@redhat.com> - 52.8.0-2
- safeguard against linking against bundled nss
  Related: #1563708

* Fri May 11 2018 Kalev Lember <klember@redhat.com> - 52.8.0-1
- Update to 52.8.0
- Fix the build on ppc
- Disable JS Helper threads on ppc64le (#1523121)

* Sat Apr 07 2018 Kalev Lember <klember@redhat.com> - 52.7.3-1
- Update to 52.7.3

* Tue Mar 20 2018 Kalev Lember <klember@redhat.com> - 52.7.2-1
- Update to 52.7.2
- Switch to %%ldconfig_scriptlets

* Thu Feb 08 2018 Fedora Release Engineering <releng@fedoraproject.org> - 52.6.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Tue Jan 23 2018 Kalev Lember <klember@redhat.com> - 52.6.0-1
- Update to 52.6.0

* Fri Nov 24 2017 Björn Esser <besser82@fedoraproject.org> - 52.5.0-5
- SpiderMonkey tests have regressions on %%{power64}, too

* Fri Nov 24 2017 Björn Esser <besser82@fedoraproject.org> - 52.5.0-4
- SpiderMonkey tests have regressions on big endian platforms

* Fri Nov 24 2017 Björn Esser <besser82@fedoraproject.org> - 52.5.0-3
- SpiderMonkey tests do not fail on any arch
- Basic JIT tests are failing on s390 arches, only
- Use macro for ppc64 arches
- Run tests using Python2 explicitly
- Simplify %%check
- Use the %%{major} macro consequently
- Replace %%define with %%global

* Fri Nov 24 2017 Björn Esser <besser82@fedoraproject.org> - 52.5.0-2
- Use macro for Python 2 interpreter
- Use proper export and quoting

* Tue Nov 14 2017 Kalev Lember <klember@redhat.com> - 52.5.0-1
- Update to 52.5.0

* Tue Oct 31 2017 Kalev Lember <klember@redhat.com> - 52.4.0-3
- Include standalone /usr/bin/js52 interpreter

* Tue Oct 31 2017 Kalev Lember <klember@redhat.com> - 52.4.0-2
- Various secondary arch fixes

* Thu Sep 28 2017 Kalev Lember <klember@redhat.com> - 52.4.0-1
- Update to 52.4.0

* Wed Sep 20 2017 Kalev Lember <klember@redhat.com> - 52.3.0-1
- Initial Fedora packaging, based on earlier mozjs45 work
