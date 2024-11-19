<div align="center">

# LRCMake

![GitHub Release](https://img.shields.io/github/v/release/Dzheremi2/LRCMake-GTK)
![GitHub License](https://img.shields.io/github/license/Dzheremi2/LRCMake-GTK)
[![Translate state](https://hosted.weblate.org/widget/lrcmake/lrcmake/svg-badge.svg)](https://hosted.weblate.org/engage/lrcmake/)

<img src="data/icons/hicolor/scalable/apps/io.github.dzheremi2.lrcmake_gtk.svg" width="150">

![Screenshot](docs/screenshots/lib.png)

</div>

### What is LRCMake
LRCMake is the app written in python using GTK4 and LibAdwaita. LRCMake is used for syncing lyrics for future contributing it to various resources, especially [LRCLIB](https://lrclib.net).

LRCMake support exporting lyrics to clipboard and direct publishing to [LRCLIB](https://lrclib.net).

### Installation

Download `.flatpak` file from the [latest release](https://github.com/Dzheremi2/LRCMake-GTK/releases/latest) and install it.

### Translation
You can help project to be internationalized using [Hosted Weblate](https://hosted.weblate.org/projects/lrcmake/lrcmake/)

##### Translation status

[![Состояние перевода](https://hosted.weblate.org/widget/lrcmake/lrcmake/287x66-black.png)](https://hosted.weblate.org/engage/lrcmake/)
[![Translate state](https://hosted.weblate.org/widget/lrcmake/lrcmake/multi-auto.svg)](https://hosted.weblate.org/engage/lrcmake/)

### Building

#### Dependencies
You'll need to install `flatpak-builder` package and `org.gnome.Platform` flatpak runtime of version `47`

#### Building

Execute this commands one-by-one:
*Replace ***{repofolder}*** with your path to repository directory*

```shell
flatpak build-init {repofolder}/.flatpak/repo io.github.dzheremi2.lrcmake_gtk org.gnome.Sdk org.gnome.Platform 47
```
```shell
flatpak-builder --ccache --force-clean --disable-updates --download-only --state-dir=/home/dzheremi/Projects/LRCMake/.flatpak/flatpak-builder --stop-at=python3-modules {repofolder}/.flatpak/repo {repofolder}/io.github.dzheremi2.lrcmake_gtk.json
```
```shell
flatpak-builder --ccache --force-clean --disable-updates --disable-download --build-only --keep-build-dirs --state-dir=/home/dzheremi/Projects/LRCMake/.flatpak/flatpak-builder --stop-at=python3-modules {repofolder}/.flatpak/repo {repofolder}/io.github.dzheremi2.lrcmake_gtk.json
```
```shell
cp -r {repofolder}/.flatpak/repo {repofolder}/.flatpak/finalized-repo
```
```shell
flatpak build-finish --share=network --share=ipc --socket=fallback-x11 --device=dri --socket=wayland --socket=pulseaudio --command=lrcmake {repofolder}/.flatpak/finalized-repo
```
```shell
flatpak build-export {repofolder}/.flatpak/ostree-repo {repofolder}/.flatpak/finalized-repo
```
```shell
flatpak build-bundle {repofolder}/.flatpak/ostree-repo io.github.dzheremi2.lrcmake_gtk.flatpak io.github.dzheremi2.lrcmake_gtk
```

### Screenshots

![](docs/screenshots/syncing.png)
![](docs/screenshots/file_info.png)