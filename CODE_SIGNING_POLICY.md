# Code signing policy

**Free code signing provided by SignPath.io, certificate by SignPath Foundation.**

Bridge Timer uses code signing only for official Windows release binaries built from this repository.

## Team roles

- **Committer / author:** [CapGui13](https://github.com/CapGui13)
- **Reviewer:** [CapGui13](https://github.com/CapGui13)
- **Approver:** [CapGui13](https://github.com/CapGui13)

Bridge Timer is currently a single-maintainer project. Signing requests for official releases are manually approved.

## Build and signing rules

- Release binaries are built from source code and build scripts in this repository.
- Release builds use GitHub-hosted runners.
- Dependency versions are pinned in `go.mod` and `go.sum`.
- The Windows artifact to be signed is `BridgeTimer.exe`.
- Product metadata is fixed to **Bridge Timer** and version metadata must match the release version.
- Private signing keys are not stored in this repository or GitHub Actions; signing keys are managed by SignPath / SignPath Foundation.
- Official signing uses SignPath origin verification and trusted-build-system verification when enabled for the project.

## Privacy

See [PRIVACY.md](PRIVACY.md).

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

## Reporting a concern

Please open an issue in this repository and identify the affected Bridge Timer version.
