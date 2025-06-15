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
install_subdir('ui', install_dir: moduledir, exclude_files: [
  'BoxDialog.pyi',
  'LrclibTrack.pyi',
  'Preferences.pyi',
  'SavedLocation.pyi',
  'SongCard.pyi',
  'SyncLine.pyi'
])
install_subdir('utils', install_dir: moduledir, exclude_files: [
  'export_data.pyi',
  'file_mutagen_id3.pyi',
  'file_mutagen_vorbis.pyi',
  'file.pyi',
  'parsers.pyi',
  'publish.pyi',
  'select_data.pyi',
  'file_mutagen_mp4.pyi'
])
install_data(
    [
    'main.py',
    'window.py',
    configure_file(input: 'internal.py.in', output: 'internal.py', configuration: conf),
  ],
  install_dir: moduledir,
)
