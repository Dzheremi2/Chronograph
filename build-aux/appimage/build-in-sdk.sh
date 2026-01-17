#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SDK_ID="org.gnome.Sdk"
SDK_VERSION="49"
PROFILE="${CHRONOGRAPH_PROFILE:-release}"
if [[ "$PROFILE" == "devel" ]]; then
  PROFILE="development"
fi

if [[ "$PROFILE" == "development" ]]; then
  APP_ID="io.github.dzheremi2.lrcmake_gtk.Devel"
else
  APP_ID="io.github.dzheremi2.lrcmake-gtk"
fi

_die() {
  echo "error: $*" >&2
  exit 1
}

_need_cmd() {
  command -v "$1" >/dev/null 2>&1 || _die "Missing required command: $1"
}

_copy_tree() {
  local src="$1"
  local dest="$2"

  mkdir -p "$dest"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$src/" "$dest/"
  else
    cp -a "$src/." "$dest/"
  fi
}

_skip_lib() {
  case "$1" in
    */ld-linux*|*/libc.so*|*/libm.so*|*/libpthread.so*|*/librt.so*|*/libdl.so*)
      return 0
      ;;
  esac
  return 1
}

_list_deps() {
  ldd "$1" | awk '{ if ($3 ~ /^\//) print $3; else if ($1 ~ /^\//) print $1 }'
}

_copy_deps_for_file() {
  local file="$1"
  local dep

  while IFS= read -r dep; do
    if _skip_lib "$dep"; then
      continue
    fi
    if [[ -f "$dep" ]]; then
      mkdir -p "$APPDIR/usr/lib"
      cp -L "$dep" "$APPDIR/usr/lib/"
    fi
  done < <(_list_deps "$file")
}

if [[ -f "/.flatpak-info" ]]; then
  SDK_OK=0
  if grep -q "sdk=${SDK_ID}//${SDK_VERSION}" "/.flatpak-info"; then
    SDK_OK=1
  elif grep -Eq "runtime=${SDK_ID}/[^/]+/${SDK_VERSION}" "/.flatpak-info"; then
    SDK_OK=1
  elif grep -q "name=${SDK_ID}" "/.flatpak-info"; then
    SDK_OK=1
  fi

  if [[ "$SDK_OK" -eq 0 ]]; then
    _die "This script must run inside ${SDK_ID}//${SDK_VERSION}."
  fi
else
  if [[ "${CHRONOGRAPH_APPIMAGE_SDK:-}" != "1" ]]; then
    _die "Run via build.sh or set CHRONOGRAPH_APPIMAGE_SDK=1 inside the GNOME SDK 49 container."
  fi
fi

_need_cmd meson
_need_cmd python3
_need_cmd pkg-config
_need_cmd ldd
_need_cmd find

_append_env_path() {
  local var_name="$1"
  local value="$2"

  if [[ -z "$value" ]]; then
    return
  fi

  local current="${!var_name:-}"
  if [[ -n "$current" ]]; then
    if [[ ":$current:" == *":$value:"* ]]; then
      return
    fi
    export "$var_name"="${value}:${current}"
  else
    export "$var_name"="$value"
  fi
}

GI_TYPELIB_DIR="$(pkg-config --variable=typelibdir gobject-introspection-1.0 2>/dev/null || true)"
_append_env_path "GI_TYPELIB_PATH" "$GI_TYPELIB_DIR"
for candidate in /usr/lib/girepository-1.0 /usr/lib64/girepository-1.0 /usr/lib/*/girepository-1.0; do
  if [[ -d "$candidate" ]]; then
    _append_env_path "GI_TYPELIB_PATH" "$candidate"
  fi
done

ARCH="$(uname -m)"
if [[ "$ARCH" != "x86_64" ]]; then
  _die "Only x86_64 AppImage builds are supported."
fi

BUILD_ROOT="${CHRONOGRAPH_BUILD_ROOT:-$ROOT/_build/appimage}"
if [[ "$BUILD_ROOT" != /* ]]; then
  BUILD_ROOT="$ROOT/$BUILD_ROOT"
fi
APPDIR="$BUILD_ROOT/AppDir"
BUILD_DIR="$BUILD_ROOT/meson"
export BUILD_DIR
DIST_DIR="$BUILD_ROOT/dist"
TOOLS_DIR="$BUILD_ROOT/tools"

rm -rf "$APPDIR" "$DIST_DIR"
mkdir -p "$APPDIR" "$DIST_DIR" "$TOOLS_DIR"

if [[ -d "$BUILD_DIR" ]]; then
  meson setup --reconfigure "$BUILD_DIR" "$ROOT" --prefix /usr \
    --wrap-mode=nofallback -Dprofile="$PROFILE"
else
  meson setup "$BUILD_DIR" "$ROOT" --prefix /usr \
    --wrap-mode=nofallback -Dprofile="$PROFILE"
fi
meson compile -C "$BUILD_DIR"
DESTDIR="$APPDIR" meson install -C "$BUILD_DIR"

PY_VER="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
PY_STDLIB="$(python3 - <<'PY'
import sysconfig
print(sysconfig.get_path("stdlib"))
PY
)"
PY_PURELIB="$(python3 - <<'PY'
import sysconfig
print(sysconfig.get_path("purelib"))
PY
)"
PY_PLATLIB="$(python3 - <<'PY'
import sysconfig
print(sysconfig.get_path("platlib"))
PY
)"

PY_BIN_NAME="python${PY_VER}"
if [[ ! -x "/usr/bin/${PY_BIN_NAME}" ]]; then
  PY_BIN_NAME="python3"
fi

mkdir -p "$APPDIR/usr/bin"
for bin in "/usr/bin/python3" "/usr/bin/python${PY_VER}"; do
  if [[ -x "$bin" ]]; then
    cp -a "$bin" "$APPDIR/usr/bin/"
  fi
done

_copy_tree "$PY_STDLIB" "$APPDIR/usr/lib/python${PY_VER}"
_copy_tree "$PY_PURELIB" "$APPDIR/usr/lib/python${PY_VER}/site-packages"
if [[ "$PY_PLATLIB" != "$PY_PURELIB" ]]; then
  _copy_tree "$PY_PLATLIB" "$APPDIR/usr/lib/python${PY_VER}/site-packages"
fi

PIP_DISABLE_PIP_VERSION_CHECK=1 \
  python3 -m pip install --root "$APPDIR" --prefix /usr \
  -r "$ROOT/build-aux/appimage/requirements.txt"

lib_paths=("$APPDIR/usr/lib")
shopt -s nullglob
for lib_dir in "$APPDIR/usr/lib/python${PY_VER}/site-packages"/*.libs \
  "$APPDIR/usr/lib/python${PY_VER}/site-packages"/*/*.libs; do
  if [[ -d "$lib_dir" ]]; then
    lib_paths+=("$lib_dir")
    for lib in "$lib_dir"/*.so*; do
      if [[ -f "$lib" ]]; then
        dest="$APPDIR/usr/lib/$(basename "$lib")"
        if [[ ! -e "$dest" ]]; then
          cp -a "$lib" "$dest"
        fi
      fi
    done
  fi
done
shopt -u nullglob

GST_PLUGINS_DIR="$(pkg-config --variable=pluginsdir gstreamer-1.0 2>/dev/null || true)"
if [[ -n "$GST_PLUGINS_DIR" && -d "$GST_PLUGINS_DIR" ]]; then
  mkdir -p "$APPDIR/usr/lib/gstreamer-1.0"
  cp -a "$GST_PLUGINS_DIR/." "$APPDIR/usr/lib/gstreamer-1.0/"
fi

GST_LIBEXEC_DIR="$(pkg-config --variable=libexecdir gstreamer-1.0 2>/dev/null || true)"
GST_SCANNER="$GST_LIBEXEC_DIR/gstreamer-1.0/gst-plugin-scanner"
if [[ -x "$GST_SCANNER" ]]; then
  mkdir -p "$APPDIR/usr/libexec/gstreamer-1.0"
  cp -a "$GST_SCANNER" "$APPDIR/usr/libexec/gstreamer-1.0/"
  _copy_deps_for_file "$GST_SCANNER"
fi

GI_DIR=""
for candidate in /usr/lib/girepository-1.0 /usr/lib64/girepository-1.0 /usr/lib/*/girepository-1.0; do
  if [[ -d "$candidate" ]]; then
    GI_DIR="$candidate"
    break
  fi
done
if [[ -n "$GI_DIR" ]]; then
  mkdir -p "$APPDIR/usr/lib/girepository-1.0"
  cp -a "$GI_DIR"/Gst*.typelib "$APPDIR/usr/lib/girepository-1.0/" 2>/dev/null || true
fi

LIBMAGIC_PATH="$(find /usr/lib /usr/lib64 /usr/lib/* -name 'libmagic.so*' -type f 2>/dev/null | head -n 1)"
if [[ -n "$LIBMAGIC_PATH" ]]; then
  mkdir -p "$APPDIR/usr/lib"
  cp -L "$LIBMAGIC_PATH" "$APPDIR/usr/lib/"
  _copy_deps_for_file "$LIBMAGIC_PATH"
fi

MAGIC_DB="$(find /usr/share -path '*/misc/magic.mgc' -type f 2>/dev/null | head -n 1)"
if [[ -n "$MAGIC_DB" ]]; then
  mkdir -p "$APPDIR/usr/share/misc"
  cp -a "$MAGIC_DB" "$APPDIR/usr/share/misc/"
fi

if [[ -d "$APPDIR/usr/lib/gstreamer-1.0" ]]; then
  while IFS= read -r plugin; do
    _copy_deps_for_file "$plugin"
  done < <(find "$APPDIR/usr/lib/gstreamer-1.0" -type f -name '*.so')
fi

ICON_FILE="$APPDIR/usr/share/icons/hicolor/scalable/apps/${APP_ID}.svg"
DESKTOP_FILE="$APPDIR/usr/share/applications/${APP_ID}.desktop"

if [[ ! -f "$DESKTOP_FILE" ]]; then
  _die "Desktop file not found at ${DESKTOP_FILE}"
fi

if [[ ! -f "$ICON_FILE" ]]; then
  _die "Icon file not found at ${ICON_FILE}"
fi

LINUXDEPLOY_URL="https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
GTK_PLUGIN_URL="https://github.com/linuxdeploy/linuxdeploy-plugin-gtk/releases/download/continuous/linuxdeploy-plugin-gtk-x86_64.AppImage"
APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"

_fetch_tool() {
  local url="$1"
  local dest="$2"

  if [[ -f "$dest" ]]; then
    return 0
  fi

  if command -v curl >/dev/null 2>&1; then
    curl -L -o "$dest" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$dest" "$url"
  else
    _die "curl or wget is required to download ${url}"
  fi

  chmod +x "$dest"
}

LINUXDEPLOY_BIN="$TOOLS_DIR/linuxdeploy-x86_64.AppImage"
APPIMAGETOOL_BIN="$TOOLS_DIR/appimagetool-x86_64.AppImage"
PLUGIN_DIR="$TOOLS_DIR/plugins"
GTK_PLUGIN_BIN="$PLUGIN_DIR/linuxdeploy-plugin-gtk.AppImage"

mkdir -p "$PLUGIN_DIR"
_fetch_tool "$LINUXDEPLOY_URL" "$LINUXDEPLOY_BIN"
_fetch_tool "$GTK_PLUGIN_URL" "$GTK_PLUGIN_BIN"
_fetch_tool "$APPIMAGETOOL_URL" "$APPIMAGETOOL_BIN"

export APPIMAGE_EXTRACT_AND_RUN=1
rm -f "$TOOLS_DIR/linuxdeploy-plugin-gtk-x86_64.AppImage"

if [[ "${#lib_paths[@]}" -gt 0 ]]; then
  new_ld_path="$(IFS=:; echo "${lib_paths[*]}")"
  if [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
    export LD_LIBRARY_PATH="${new_ld_path}:${LD_LIBRARY_PATH}"
  else
    export LD_LIBRARY_PATH="$new_ld_path"
  fi
fi

GTK_PLUGIN_WRAPPER="$PLUGIN_DIR/linuxdeploy-plugin-gtk"
cat > "$GTK_PLUGIN_WRAPPER" <<EOF
#!/usr/bin/env bash
export APPIMAGE_EXTRACT_AND_RUN=1
exec "$GTK_PLUGIN_BIN" "\$@"
EOF
chmod +x "$GTK_PLUGIN_WRAPPER"

export LINUXDEPLOY_PLUGIN_PATH="$PLUGIN_DIR"

"$LINUXDEPLOY_BIN" \
  --appdir "$APPDIR" \
  --desktop-file "$DESKTOP_FILE" \
  --icon-file "$ICON_FILE" \
  --executable "$APPDIR/usr/bin/${PY_BIN_NAME}"

_collect_gschemas() {
  local schema_dir="$APPDIR/usr/share/glib-2.0/schemas"
  mkdir -p "$schema_dir"
  if [[ -d "/usr/share/glib-2.0/schemas" ]]; then
    cp -a /usr/share/glib-2.0/schemas/*.xml "$schema_dir/" 2>/dev/null || true
  fi
  for d in /usr/share/glib-2.0/schemas /usr/lib/*/glib-2.0/schemas; do
    if [[ -d "$d" ]]; then
      cp -a "$d"/*.xml "$schema_dir/" 2>/dev/null || true
    fi
  done
  if command -v glib-compile-schemas >/dev/null 2>&1; then
    glib-compile-schemas "$schema_dir"
  fi
}

_collect_gtk_data() {
  local datadir="$APPDIR/usr/share"
  for d in /usr/share/gtk-4.0 /usr/share/libadwaita-1 /usr/share/icons/Adwaita; do
    if [[ -d "$d" ]]; then
      _copy_tree "$d" "$datadir/$(basename "$d")"
    fi
  done
  if command -v gtk4-update-icon-cache >/dev/null 2>&1; then
    gtk4-update-icon-cache -q -t -f "$APPDIR/usr/share/icons/hicolor" || true
  fi
}

_collect_gschemas
_collect_gtk_data

APP_RUN="$APPDIR/AppRun"
rm -f "$APP_RUN"
cat > "$APP_RUN" <<EOF
#!/usr/bin/env sh
set -e
APPDIR="\$(cd "\$(dirname "\$0")" && pwd)"
export PYTHONHOME="\${APPDIR}/usr"
export PYTHONPATH="\${APPDIR}/usr/lib/python${PY_VER}/site-packages:\${PYTHONPATH:-}"
export GI_TYPELIB_PATH="\${APPDIR}/usr/lib/girepository-1.0:\${GI_TYPELIB_PATH:-}"
export MAGIC="\${APPDIR}/usr/share/misc/magic.mgc"
export GST_PLUGIN_PATH="\${APPDIR}/usr/lib/gstreamer-1.0"
export GST_PLUGIN_SYSTEM_PATH="\${GST_PLUGIN_PATH}"
export GST_PLUGIN_SCANNER="\${APPDIR}/usr/libexec/gstreamer-1.0/gst-plugin-scanner"
export GSETTINGS_SCHEMA_DIR="\${APPDIR}/usr/share/glib-2.0/schemas"
export XDG_DATA_DIRS="\${APPDIR}/usr/share:\${XDG_DATA_DIRS:-}"
exec "\${APPDIR}/usr/bin/${PY_BIN_NAME}" "\${APPDIR}/usr/bin/chronograph" "\$@"
EOF
chmod +x "$APP_RUN"

APP_VERSION="$(python3 - <<'PY'
import json
import os
import subprocess
import sys

build_dir = os.environ.get("BUILD_DIR", "")
info_path = os.path.join(build_dir, "meson-info", "projectinfo.json")

data = None
if info_path and os.path.exists(info_path):
  with open(info_path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
else:
  try:
    output = subprocess.check_output(
      ["meson", "introspect", "--projectinfo", build_dir],
      text=True,
    )
    data = json.loads(output)
  except Exception:
    data = None

version = "unknown"
if isinstance(data, dict):
  version = data.get("version") or version

print(version)
PY
)"

APPIMAGE_NAME="Chronograph-${APP_VERSION}-${ARCH}.AppImage"
if [[ "$PROFILE" == "development" ]]; then
  APPIMAGE_NAME="Chronograph-Devel-${APP_VERSION}-${ARCH}.AppImage"
fi

"$APPIMAGETOOL_BIN" \
  "$APPDIR" \
  "$DIST_DIR/$APPIMAGE_NAME"

echo "AppImage created at ${DIST_DIR}/${APPIMAGE_NAME}"
