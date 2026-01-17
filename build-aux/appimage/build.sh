#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SDK_ID="org.gnome.Sdk"
SDK_VERSION="49"
PROFILE="${1:-${CHRONOGRAPH_PROFILE:-release}}"
BUILD_ROOT="${CHRONOGRAPH_BUILD_ROOT:-$ROOT/_build/appimage}"
export CHRONOGRAPH_PROFILE="$PROFILE"
export CHRONOGRAPH_BUILD_ROOT="$BUILD_ROOT"

if [[ -f "/.flatpak-info" ]]; then
  exec "$ROOT/build-aux/appimage/build-in-sdk.sh"
fi

if ! command -v flatpak >/dev/null 2>&1; then
  echo "error: flatpak is required to build the AppImage." >&2
  exit 1
fi

if ! flatpak info --show-ref "${SDK_ID}//${SDK_VERSION}" >/dev/null 2>&1; then
  echo "error: ${SDK_ID}//${SDK_VERSION} is not installed." >&2
  echo "Install it with: flatpak install flathub ${SDK_ID}//${SDK_VERSION}" >&2
  exit 1
fi

mkdir -p "$BUILD_ROOT"

extra_fs=()
if [[ "$BUILD_ROOT" != "$ROOT/_build/appimage" ]]; then
  extra_fs+=(--filesystem="$BUILD_ROOT")
fi

flatpak run \
  --filesystem="$ROOT" \
  --share=network \
  --env=CHRONOGRAPH_PROFILE="$PROFILE" \
  --env=CHRONOGRAPH_BUILD_ROOT="$BUILD_ROOT" \
  "${extra_fs[@]}" \
  --command=sh \
  "${SDK_ID}//${SDK_VERSION}" \
  -c "$ROOT/build-aux/appimage/build-in-sdk.sh"
