# AppImage build

Chronograph's AppImage is built using GNOME SDK 49 to match the runtime library
versions used by the Flatpak build.

## Build locally

1. Install the SDK:
   `flatpak install flathub org.gnome.Sdk//49`
2. Run the build script:
   `./build-aux/appimage/build.sh`

The AppImage will be placed in `_build/appimage/dist/`.

To build the development profile, run:
`./build-aux/appimage/build.sh development`

The build script downloads linuxdeploy, linuxdeploy-plugin-gtk, and appimagetool,
and installs pinned Python dependencies via pip.
