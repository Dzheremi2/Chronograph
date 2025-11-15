<div align="center">

<img src="data/icons/hicolor/scalable/apps/io.github.dzheremi2.lrcmake-gtk.svg" width="128" height="128">

# Chronograph
**_Sync Lyrics of Your Loved Songs_** 🕒

[flathub-url]: https://flathub.org/apps/io.github.dzheremi2.lrcmake-gtk
[installs-img]: https://img.shields.io/flathub/downloads/io.github.dzheremi2.lrcmake-gtk?style=for-the-badge&color=gree&logo=flathub

[![GitHub Release](https://img.shields.io/github/v/release/Dzheremi2/Chronograph?include_prereleases&style=for-the-badge&color=000B3C&logo=github)](https://github.com/Dzheremi2/Chronograph/releases/)
<a href="https://flathub.org/apps/io.github.dzheremi2.lrcmake-gtk"><img alt="Flathub Version" src="https://img.shields.io/flathub/v/io.github.dzheremi2.lrcmake-gtk?style=for-the-badge&logo=flathub&color=lightblue"></a>
[![Installs][installs-img]][flathub-url]
[![Weblate project translated](https://img.shields.io/weblate/progress/chronograph?style=for-the-badge&logo=weblate&logoColor=white&logoSize=auto&color=magenta&cacheSeconds=600)](https://hosted.weblate.org/projects/lrcmake/chronograph/)
<a href="https://github.com/Dzheremi2/Chronograph/actions"><img alt="GitHub Actions Workflow Status" src="https://img.shields.io/github/actions/workflow/status/Dzheremi2/Chronograph/.github%2Fworkflows%2Fci.yml?style=for-the-badge&logo=github"></a>
[![GitHub License](https://img.shields.io/github/license/Dzheremi2/Chronograph?style=for-the-badge&color=C25D00)](https://github.com/Dzheremi2/Chronograph/blob/master/LICENSE)

![Screenshot](docs/screenshots/libB.png)

</div>

### About Chronograph
Chronograph is an open-source application designed for accurately syncing lyrics with 
audio timestamps.

You may notice that many of music players support synced lyrics which are highlighted 
line-by-line or word-by-word while playing? This app was designed to give the community an 
ability to be the ones who make these lyrics.

Chronograph directly supports publishing to [LRCLib](https://lrclib.net). As many FOSS 
music players use LRCLib to fetch synchronized lyrics, this integration allows users to 
easily contribute their work back to the open-source community.

**Syncing Modes**
- **Line-by-Line (Primary)**: Here, every time you do sync action, timestamp is placed for 
the whole line of lyrics. This is the most supported format of synced lyrics.
- **Word-by-Word (Advanced)**: Designed for true karaoke quality. It places a timestamp 
for every single word, enabling players to animate lyrics with precision.

**Supported Formats**
- OGG
- FLAC
- MP3
- M4A
- OPUS
- WAV
- AAC (reduced functionality)

### Installation
<a href='https://flathub.org/apps/io.github.dzheremi2.lrcmake-gtk'>
    <img width='240' alt='Get it on Flathub' src='https://flathub.org/api/badge?svg&locale=en'/>
</a>

You can download app either on [Flathub](https://flathub.org/apps/io.github.dzheremi2.lrcmake-gtk) 
or by downloading and installing bundle from the [latest release](https://github.com/Dzheremi2/Chronograph/releases/latest)

### Releases

Chronograph has three types of releases *stable*, *release candidates (beta)* and 
*devel (alpha)*

#### Stable

Stable releases are available on Fridays (if not a hotfix) if their develepment cycle has 
ended. Could be downloaded either on [Flathub](https://flathub.org/apps/io.github.dzheremi2.lrcmake-gtk) 
or via [GitHub Releases]((https://github.com/Dzheremi2/Chronograph/releases/latest))

#### Release Candidate

RCs are published before the stable release in friday-awaiting time for users to be able 
to test them and report bugs before the release happens.
Could be downloaded only on [GitHub Releases](https://github.com/Dzheremi2/Chronograph/releases/). 
RCs are marked as `Pre-release`

#### Devel

Devel build are formed for every commit on any branch except for `main`. These build are 
casts of the current development state, so treat them as *Alpha* releases

>[!CAUTION]
>Devel builds may be unstable or don't even launch. Use it at your own risk

### Changelog
You can see full changelog for all versions [here](docs/CHANGELOG.md)

### Translation
You can help project to be internationalized using [Hosted Weblate](https://hosted.weblate.org/projects/chronograph/chronograph/)

##### Translation status

[![Состояние перевода](https://hosted.weblate.org/widget/chronograph/chronograph/287x66-black.png)](https://hosted.weblate.org/engage/chronograph/)
[![Translate state](https://hosted.weblate.org/widget/chronograph/chronograph/multi-auto.svg)](https://hosted.weblate.org/engage/chronograph/)

### Plans
You can see future plans on Projects page of this repo on [Chronograph roadmap.](https://github.com/users/Dzheremi2/projects/2)

If you have an idea or you know a bug, please, open an [issue](https://github.com/Dzheremi2/Chronograph/issues) 
with you idea/bug and it will be added to roadmap.

If you want the app to support more file formats, create a feature request about that and 
attach a sample file.

### Code of Conduct
The project follows the [GNOME Code of Conduct](https://conduct.gnome.org)

### Contributing
All contribution instructions are described in [CONTRIBUTING.md](https://github.com/Dzheremi2/Chronograph/blob/master/CONTRIBUTING.md) 
file.

### Screenshots
<div align="center">

![](docs/screenshots/libLB.png)
![](docs/screenshots/libW.png)
![](docs/screenshots/libLW.png)
![](docs/screenshots/syncB.png)
![](docs/screenshots/syncCB.png)
![](docs/screenshots/syncW.png)
![](docs/screenshots/syncCW.png)
![](docs/screenshots/lrclibB.png)
![](docs/screenshots/lrclibW.png)
![](docs/screenshots/wbwsyncB.png)
![](docs/screenshots/wbwsyncW.png)
![](docs/screenshots/wbweditB.png)
![](docs/screenshots/wbweditW.png)

</div> 