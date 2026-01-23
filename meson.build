project('chronograph',
          version: '49',
    meson_version: '>= 1.0.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

i18n = import('i18n')
gnome = import('gnome')
python = import('python')

py_installation = python.find_installation('python3')

cachev = 2
dbver = 1
python = import('python')
pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())

profile = get_option('profile')
if profile == 'development'
    app_id = 'io.github.dzheremi2.lrcmake_gtk.Devel'
    prefix = '/io/github/dzheremi2/lrcmake_gtk/Devel'
elif profile == 'release'
    app_id = 'io.github.dzheremi2.lrcmake-gtk'
    prefix = '/io/github/dzheremi2/lrcmake-gtk'
endif

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('APP_ID', app_id)
conf.set('PREFIX', prefix)
conf.set('CACHEV', cachev)
conf.set('DBVER', dbver)
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix') / get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

subdir('data')
subdir('chronograph')

include_dgutils = get_option('include_dgutils')
if include_dgutils == 'true'
    install_subdir('dgutils', install_dir: pkgdatadir)
endif

subdir('po')

gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
