# Ued to support devel/stable icon in window.blp depending on build type
window = custom_target('window',
  input: configure_file(input: 'window.blp.in', output: 'window.blp', configuration: conf),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', join_paths(get_option('datadir'), 'gtk'), '@INPUT@'],
)
