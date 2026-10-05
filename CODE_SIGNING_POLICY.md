# Code signing policy

Bridge Timer is currently distributed as an **unsigned portable Windows executable**.

A request for the SignPath Foundation free code-signing program was reviewed in October 2026 but was not approved because the project did not yet meet the program's public visibility/adoption threshold. This was not a technical rejection of Bridge Timer.

## Current distribution

- The Windows application is delivered as a single `BridgeTimer.exe`.
- No installer is used.
- Official binaries are built from this repository on GitHub-hosted Windows runners.
- Dependency versions are pinned in `go.mod` and `go.sum`.
- Product and file-version metadata must match the source version.
- Because current builds are unsigned, Windows may display a SmartScreen or reputation warning on first launch.

## Future signing

Code signing may be added later through a suitable certificate provider or through SignPath Foundation if the project becomes eligible.

No private signing key is stored in this repository.

## Privacy

See [PRIVACY.md](PRIVACY.md).

This program will not transfer any information to other networked systems unless specifically requested by the user or the person operating it.

## Reporting a concern

Please open an issue in this repository and identify the affected Bridge Timer version.
