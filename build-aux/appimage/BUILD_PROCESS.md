# AppImage build process

>[!IMPORTANT]
>The AppImage buildscript was made by Chat GPT Codex, since the maintainer does not know
>bash at all.

This file explains how the AppImage build scripts work and why each step exists.
The goal is to build Chronograph with the same library versions as GNOME SDK 49.

## Entry point

Use `build-aux/appimage/build.sh` locally.
It checks for `org.gnome.Sdk//49` and starts a Flatpak SDK shell if needed, then
executes `build-aux/appimage/build-in-sdk.sh` inside that SDK runtime.

## Build flow inside the SDK

`build-aux/appimage/build-in-sdk.sh` performs these steps in order:

1) Configure and compile with Meson
  - Uses the repo root as the source directory.
  - Builds into `_build/appimage/meson`.
  - Installs into `AppDir` via `DESTDIR`, so output lands in
    `_build/appimage/AppDir/usr/...`.

2) Bundle Python runtime + deps
  - Copies the SDK Python interpreter and stdlib into `AppDir/usr`.
  - Installs pinned Python dependencies from
    `build-aux/appimage/requirements.txt` into `AppDir/usr`.
  - Copies any `*.libs` folders (for packages like Pillow) into
    `AppDir/usr/lib` so linuxdeploy can resolve their dependencies.

3) Bundle media stack + extras
  - Copies GStreamer plugins and `gst-plugin-scanner`.
  - Copies required typelibs for Gst/GstPlay.
  - Bundles `libmagic` and its `magic.mgc` database.

4) Build AppDir with linuxdeploy
  - Runs linuxdeploy to collect ELF dependencies and set up AppDir layout.
  - The GTK plugin is not used; GTK/LibAdwaita data and schemas are collected
    manually to avoid plugin issues inside the SDK container.

5) Add schemas and GTK data
  - Copies schemas into `AppDir/usr/share/glib-2.0/schemas`.
  - Runs `glib-compile-schemas`.
  - Copies GTK and LibAdwaita data, plus Adwaita icon theme data.

6) Create AppRun wrapper
  - Replaces linuxdeploy's AppRun with a shell wrapper that sets:
    - `APPDIR` aware paths for data, locales, typelibs, and magic db
    - GStreamer plugin paths and scanner location
    - GTK schema dir and XDG data dirs
  - Executes `pythonX.Y` with the installed `chronograph` launcher.

7) Package with appimagetool
  - Reads version from Meson project info.
  - Produces `_build/appimage/dist/Chronograph-<version>-x86_64.AppImage`.

## Notes and constraints

- The AppImage is built against GNOME SDK 49 to match the Flatpak runtime ABI.
- The build currently supports `x86_64` only.
- Network access is required to download linuxdeploy/appimagetool and pip wheels.
- The launcher respects `APPDIR` so resources are resolved inside the AppImage.
