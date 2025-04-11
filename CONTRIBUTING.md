# Contributing

## Indirect Contributing
>[!TIP]
>Any issue that's already resolved but not published yet is marked with `fix-available` label. If the issue is closed, then it was already published.
#### Feature Requests
If you want some feature to be implemented within the app, [create](https://github.com/Dzheremi2/Chronograph/issues) an issue with `Feature Request` template and describe what you want to be implemented. The more information about the feature you provide, the faster, and precisely, it would be implemented.

#### Bug Reports
If you found a bug, and you're not that lazy, then you should report this bug by [creating](https://github.com/Dzheremi2/Chronograph/issues) an issue with `Bug Report` template and provide as much information about it as possible.

>[!NOTE]
>If your issue got an `unable-reproduce` label, then you probably should give more information about how it can be reproduced. Or this just means that this issue belongs only to your side. Anyway, issues with `unable-reproduce` wouldn't be worked on until they have got reproduced (`successfully-reproduced` label)

## Direct Contributing
#### Code Contributing
To directly contribute to the app, [fork](https://github.com/Dzheremi2/Chronograph/fork) the repo, make your changes and [open](https://github.com/Dzheremi2/Chronograph/pulls) a pull request. If your code satisfies the maintainer, then it would be merged, and you will be mentioned in the upcoming release and added to the `About App` section in the app.

>[!IMPORTANT]
>Code in pull requests should respect the [Project's Code Style](#code-style).

#### Internationalization
Another way to contribute to the app is internationalization. The app's using the [Hosted Weblate](https://hosted.weblate.org/projects/chronograph/chronograph/) for this purpose. If you're a translator, you could mention yourself by adding `Your Name`, `Your Name <your@e.mail>` or `Your Name https://your.site` to the `translator-credits` [string](https://hosted.weblate.org/translate/chronograph/chronograph/fi/?checksum=deecda9491124d4f&sort_by=-priority,position). This will add you to the `Translators` section in the `About App` for your language.

![](docs/screenshots/translator-credits.png)

## Build
In VSCode you can install [Flatpak](https://marketplace.visualstudio.com/items?itemName=bilelmoussaoui.flatpak-vscode) extension, select needed manifest (should be `build-aux/flatpak/io.github.dzheremi2.lrcmake_gtk.Devel.yaml`) and then use `Flatpak: Build` command from VSCode command palette.

##### Dependencies:
org.gnome.Platform (v48)
```shell
flatpak install org.gnome.Platform/x86_64/48 --system
```
org.gnome.Sdk (v48)
```shell
flatpak install org.gnome.Sdk/x86_64/48 --system
```

## Code Style
The code is formatted by [Black](https://github.com/psf/black) formatter. Imports are sorted by [isort](https://github.com/pycqa/isort).
The main IDE for developing this project is VSCode. Extensions for both these are available on VSCode Marketplace. The current configuration is embedded within the repo (`.vscode/settings.json`)

All new methods should be type hinted, static variables should be type hinted too. All methods should have docstrings in numpy docstring format ([extension](https://marketplace.visualstudio.com/items?itemName=njpwerner.autodocstring) for automatic docstrings generation)
After you're done with your feature or bug fix, please, don't forget to update corresponding `.pyi` files (if you're creating new `.py` files, don't forget to create corresponding `.pyi` files too)
>[!NOTE]
>If you're too lazy to do all these things, please, mention it in your pull request message for the maintainers to do this instead of you.

>[!TIP]
> Also, if you don't understand something, you could research the repo structure or ask the maintainer for help on the [Discussions](https://github.com/Dzheremi2/Chronograph/discussions)