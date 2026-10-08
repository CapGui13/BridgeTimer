# Bridge Timer

Bridge Timer is a portable Windows timer for bridge tournaments.

It provides a large projection-friendly countdown, round management, configurable breaks and end-of-round timing, temporary messages, three named tournament profiles, color customization, multi-screen selection, fullscreen display, local settings persistence, and import/export of `.bridge-timer` configuration files.

The application uses an embedded Microsoft Edge WebView2 view so the timer keeps the HTML/CSS rendering of the original Bridge Timer interface while remaining a standalone Windows application.

## Current version

**1.7.8**

Run `BridgeTimer.exe`. No installer is required.

## Features

- configurable time per round, number of rounds and starting round;
- Paires / Match par 4 tournament modes;
- orange/red warning thresholds;
- configurable end-of-round delay and message;
- temporary message button and `M` shortcut;
- three named profiles;
- Accent / Background / Menu / Text color settings;
- optional club logo;
- projection monitor selection and fullscreen;
- automatic local persistence of settings;
- import/export of `.bridge-timer` settings;
- Per-Monitor DPI Awareness V2;
- native Windows anti-sleep protection while the timer is running;
- hidden diagnostics with `Ctrl+Shift+D`;
- rotating local diagnostic log and backup recovery for window state;
- backup recovery for settings and profiles;
- stricter validation of imported `.bridge-timer` files;
- WebView2 grayscale text antialiasing (`--disable-lcd-text`) for cleaner large timer digits;
- single-instance Windows application;\n- monotonic countdown timing with delayed-tick catch-up;\n- dynamic loopback port to avoid local port collisions.

## Build

Official Windows builds are produced from this repository on GitHub-hosted Windows runners.

The dependency versions are pinned in `go.mod` and `go.sum`.

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
