# Bridge Timer

> **Version de référence validée le 29 octobre 2026 (Windows 10).**
> Les bandeaux des paramètres, les dimensions adaptatives de fenêtre et les
> transitions Paramètres/Timer ont été validés en essai utilisateur.
> Les tests automatisés de géométrie, de chrono, d'alertes et de fenêtre
> Windows sont obligatoires dans GitHub Actions. L'audibilité réelle des
> alarmes et la tenue d'une séance prolongée restent à confirmer sur PC.
> Revenir à `sauvegarde-bridge-timer-valide-20261029` en cas de régression.

> **RÈGLES VISUELLES IMPÉRATIVES — NE PAS INTRODUIRE DE RÉGRESSION :**
> lire [UI_LAYOUT_CONTRACT.md](UI_LAYOUT_CONTRACT.md) et préserver les tests.
> **Homothétie** : le mode fenêtré et le plein écran sont EXACTEMENT la même
> maquette 1600×900 agrandie par un coefficient uniforme unique, pour TOUS
> les éléments (titre, chrono, boutons, espaces, footer et messages).
> **Parité court / long** : les grands chiffres et leur position verticale
> sous l'évènement doivent être les mêmes dans les deux formats.
> Seuls changent la présentation du temps (`MM:SS` contre `H:MM SS`)
> et les secondes à **56 %** en format long. Le format est fixé d'après
> la durée **initiale** du tour. Toute modification doit préserver ces deux
> invariants.

Bridge Timer is a portable Windows timer for bridge tournaments.

It provides a large projection-friendly countdown, round management, configurable breaks, temporary messages, color customization with a reusable saved color preset, fullscreen display, and local settings persistence.

The application uses an embedded Microsoft Edge WebView2 view so the timer keeps the HTML/CSS rendering of the original Bridge Timer interface while remaining a standalone Windows application.

## Current version

**1.7.8**

Run `BridgeTimer.exe`. No installer is required.

## Features

- configurable time per round, number of rounds and starting round;
- Paires / Match par 4 tournament modes;
- tournament structure locked once a session is running; timing changes apply from the next round;
- Mitchell jump reminder preserved even when the between-round delay is 0 seconds;
- orange/red warning thresholds;
- temporary message button and `M` shortcut;
- Accent / Background / Menu / Text color settings;
- fullscreen projection mode and Windows-maximized display;
- automatic local persistence of settings;
- Per-Monitor DPI Awareness V2;
- native Windows anti-sleep protection while the timer is running;
- hidden diagnostics with `Ctrl+Shift+D`;
- rotating local diagnostic log;
- backup recovery for settings and saved colors;
- WebView2 grayscale text antialiasing (`--disable-lcd-text`) for cleaner large timer digits;
- single-instance Windows application;
- monotonic countdown timing with delayed-tick catch-up;
- stable local WebView origin so saved settings persist between launches;
- centered startup window with dark native/WebView2 rendering to avoid white flashes.

## Build

Official Windows builds are produced from this repository on GitHub-hosted Windows runners.

Before distributing a build, the CI workflow executes:
- JavaScript syntax and regression checks;
- Microsoft Edge visual, windowed-band and 15-scenario functional tests;
- 10 long-countdown, sound and anti-sleep tests;
- Windows native geometry tests (including a real hidden HWND) and Win32 anti-sleep tests;
- `go vet`, Windows GUI compilation, and an embedded-HTML consistency check.

The dependency versions are pinned in `go.mod` and `go.sum`.
The last tested build can be downloaded from the GitHub Actions run artifacts.
See [STABILISATION_2026-10-29.md](STABILISATION_2026-10-29.md) for
reference commits, verification boundaries, and safe rollback instructions.

## License

Bridge Timer is open source under the [MIT License](LICENSE).

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for third-party components.

## Privacy

See [PRIVACY.md](PRIVACY.md).

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

## Windows executable and signing

Bridge Timer is distributed as a portable `BridgeTimer.exe`: there is no installer.

Current public builds are unsigned. Windows may therefore show a SmartScreen or reputation warning on first launch. The source and build workflow are public in this repository.

See [CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md).

## Removal

Bridge Timer has no installer. Delete `BridgeTimer.exe` to remove it. To also remove its saved local settings, delete `%LOCALAPPDATA%\BridgeTimerWebView2`.
