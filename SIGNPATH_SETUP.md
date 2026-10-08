# SignPath Foundation setup

Bridge Timer is prepared for a future re-application to SignPath Foundation's free open-source code-signing program. The October 2026 application was not approved because the project had not yet reached the program's public visibility/adoption threshold.

Before applying:

1. Keep this repository public.
2. Keep the MIT license, privacy policy and **Code signing policy** linked from the README.
3. Enable multi-factor authentication for the GitHub maintainer account and SignPath account.
4. Publish an unsigned public release of Bridge Timer in the same executable form that will later be signed.
5. Keep official builds on GitHub-hosted runners.

Application page:

https://signpath.org/apply.html

Suggested project information:

- Project: **Bridge Timer**
- Repository: **https://github.com/CapGui13/BridgeTimer**
- License: **MIT**
- Artifact: **BridgeTimer.exe**
- Description: Portable Windows bridge-tournament timer with projection/fullscreen support.
- Code signing policy: `CODE_SIGNING_POLICY.md`
- Privacy policy: `PRIVACY.md`

After acceptance, configure the SignPath project and GitHub trusted build system, then add the repository variables/secrets referenced by `.github/workflows/sign-release.yml`.

Do not commit API tokens or signing credentials.
