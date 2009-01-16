%if 0%{?fedora}
# FC9 doesn't define 'fedora_version' but apparently OpenSUSE Build Service's FC9 does
%{!?fedora_version: %define fedora_version %fedora}
%endif

%if 0%{?mdkver}
# Mandriva 2009 doesn't define 'mandriva_version' but apparently OpenSUSE Build Service's MDK2009 does
%{!?mandriva_version: %define mandriva_version %(echo %{mdkver} | grep -o ^2...)}
%endif


%if 0%{?fedora_version} || 0%{?rhel_version} || 0%{?centos_version}
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%endif

%if 0%{?mandriva_version}
%define python_compile_opt python -O -c "import compileall; compileall.compile_dir('.')"
%define python_compile     python -c "import compileall; compileall.compile_dir('.')"
%endif

%if 0%{?suse_version}
%define python_sitelib %py_sitedir
%endif

Name:           bleachbit
Version:        0.3.0
Release:        1%{?dist}
Summary:        Remove unnecessary files, free space, and maintain privacy

%if 0%{?mandriva_version}
Group:          File tools
%else
Group:          Applications/System
%endif
License:        GPLv3
URL:            http://bleachbit.sourceforge.net
Source0:        %{name}-%{version}.tar.bz2
%if 0%{?mandriva_version}
BuildRoot:      %{_tmppath}/%{name}-%{version}
%else
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
%endif

BuildArch:      noarch

%if 0%{?mandriva_version}
BuildRequires:  libpython2.5-devel
Requires:       gnome-python
Requires:       gnome-python-gnomevfs
Requires:       pygtk2.0 >= 2.6
Requires(post): desktop-file-utils
Requires(postun): desktop-file-utils
%endif

%if 0%{?fedora_version} || 0%{?rhel_version} || 0%{?centos_version}
BuildRequires:  desktop-file-utils
BuildRequires:  python-devel
Requires:       gnome-python2-gnomevfs
Requires:       pygtk2 >= 2.6
Requires:       usermode
%endif

%if 0%{?suse_version}
BuildRequires:  make
BuildRequires:  python-devel
BuildRequires:  update-desktop-files
Requires:       python-gnome
Requires:       python-gtk >= 2.6
Requires:       xdg-utils
%py_requires
%endif

Requires:       python >= 2.4


%description
BleachBit deletes unnecessary files to free valuable disk space and
maintain privacy. Rid your system of old junk including broken
menu entries, cache, cookies, localizations, and temporary files.
Designed for Linux  systems, it wipes clean Bash, Beagle, Epiphany,
Firefox, Flash, GNOME, Java, KDE, OpenOffice.org, Opera, RealPlayer,
VIM, XChat, and more.


%prep
%setup -q


%build
%{__python} setup.py build

cp %{name}.desktop %{name}-root.desktop
sed -i -e 's/Name=BleachBit$/Name=BleachBit as Administrator/g' %{name}-root.desktop

%if 0%{?fedora_version} || 0%{?rhel_version} || 0%{?centos_version} || 0%{?mandriva_version}

cat > bleachbit.pam <<EOF
#%PAM-1.0
auth		include		config-util
account		include		config-util
session		include		config-util
EOF

cat > bleachbit.console <<EOF
USER=root
PROGRAM=/usr/share/bleachbit/GUI.py
SESSION=true
EOF

%endif


%install
rm -rf $RPM_BUILD_ROOT

make install DESTDIR=$RPM_BUILD_ROOT prefix=%{_prefix}

%if 0%{?fedora_version} || 0%{?rhel_version} || 0%{?centos_version}
desktop-file-validate %{buildroot}/%{_datadir}/applications/%{name}.desktop

sed -i -e 's/Exec=bleachbit$/Exec=bleachbit-root/g' %{name}-root.desktop

desktop-file-install \
	--dir=%{buildroot}/%{_datadir}/applications/ \
	--vendor="" %{name}-root.desktop

# consolehelper and userhelper
ln -s consolehelper %{buildroot}/%{_bindir}/%{name}-root
mkdir -p %{buildroot}/%{_sbindir}
ln -s ../..%{_datadir}/%{name}/GUI.py %{buildroot}/%{_sbindir}/%{name}-root
mkdir -p %{buildroot}%{_sysconfdir}/pam.d
install -m 644 %{name}.pam %{buildroot}%{_sysconfdir}/pam.d/%{name}-root
mkdir -p %{buildroot}%{_sysconfdir}/security/console.apps
install -m 644 %{name}.console %{buildroot}%{_sysconfdir}/security/console.apps/%{name}-root

%endif


%if 0%{?suse_version}
%suse_update_desktop_file %{name}
sed -i -e 's/^Exec=bleachbit$/Exec=xdg-su -c bleachbit/g' %{name}-root.desktop
desktop-file-install \
	--dir=%{buildroot}/%{_datadir}/applications/ \
	--vendor="" %{name}-root.desktop
%endif


make -C po install DESTDIR=$RPM_BUILD_ROOT

%find_lang %{name}


%clean
rm -rf $RPM_BUILD_ROOT

%if 0%{?fedora_version} || 0%{?rhel_version} || 0%{?centos_version}
%post
update-desktop-database &> /dev/null ||:

%postun
update-desktop-database &> /dev/null ||:
%endif

%if 0%{?mandriva_version}
%post
%{update_menus}
%{update_desktop_database}

%postun
%{clean_menus}
%{clean_desktop_database}
%endif



%files -f %{name}.lang
%defattr(-,root,root,-)
%doc COPYING
%if 0%{?fedora_version} || 0%{?rhel_version} || 0%{?centos_version} || 0%{?mandriva_version}
%config(noreplace) %{_sysconfdir}/pam.d/%{name}-root
%config(noreplace) %{_sysconfdir}/security/console.apps/%{name}-root
%{_bindir}/%{name}-root
%{_sbindir}/%{name}-root
%endif
%{_bindir}/%{name}
%{_datadir}/applications/%{name}.desktop
%{_datadir}/applications/%{name}-root.desktop
%{_datadir}/%{name}/
%{_datadir}/pixmaps/%{name}.png




%changelog
