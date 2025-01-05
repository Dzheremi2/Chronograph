pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'chronograph'
gnome = import('gnome')

configure_file(
  input: 'chronograph.in',
  output: 'chronograph',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)
install_subdir('ui', install_dir: moduledir)
install_subdir('utils', install_dir: moduledir)
install_data(
    [
    'main.py',
    'window.py',
    configure_file(input: 'shared.py.in', output: 'shared.py', configuration: conf),
  ],
  install_dir: moduledir,
)
