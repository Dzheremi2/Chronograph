subdir('gtk')

blueprints = custom_target('blueprints',
  input: files(
    'gtk/ui/widgets/SongCard.blp',
    'gtk/ui/dialogs/BoxDialog.blp',
    'gtk/ui/dialogs/LRClib.blp',
    'gtk/ui/widgets/LRClibTrack.blp',
    'gtk/ui/dialogs/Preferences.blp',
    'gtk/ui/dialogs/MetadataEditor.blp',
    'gtk/ui/dialogs/ResyncAllAlertDialog.blp',
    'gtk/ui/widgets/SavedLocation.blp',
    'gtk/ui/widgets/UIPlayer.blp',
    'gtk/ui/sync_pages/LRCSyncPage.blp',
    'gtk/ui/sync_pages/WBWSyncPage.blp',
    'gtk/ui/widgets/wbw/WordWidget.blp',
    'gtk/ui/widgets/wbw/LyricsWidget.blp',
    'gtk/ui/shortcuts-dialog.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

subdir('resources')

gnome.compile_resources(
  'Chronograph',
  configure_file(
    input: 'Chronograph.gresource.xml.in',
    output: 'Chronograph.gresource.xml',
    configuration: conf
  ),
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: [blueprints, window]
)

desktop_file = i18n.merge_file(
    input: configure_file(
        input: 'io.github.dzheremi2.lrcmake-gtk.desktop.in',
        output: app_id + '.desktop.in',
        configuration: conf
    ),
    output: app_id + '.desktop',
    type: 'desktop',
    po_dir: '../po',
    install: true,
    install_dir: join_paths(get_option('datadir'), 'applications')
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

appstream_file = i18n.merge_file(
    input: configure_file(
        input: 'io.github.dzheremi2.lrcmake-gtk.metainfo.xml.in',
        output: app_id + '.metainfo.xml.in',
        configuration: conf,
    ),
    output: app_id + '.metainfo.xml',
    po_dir: '../po',
    install: true,
    install_dir: join_paths(get_option('datadir'), 'metainfo'),
)

appstreamcli = find_program('appstreamcli', required: false, disabler: true)
test('Validate appstream file', appstreamcli,
     args: ['validate', '--no-net', '--explain', appstream_file])

subdir('icons')
