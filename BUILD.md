# Windows Build And Release

Validated with 64-bit CPython 3.13.14, with Tkinter and pip installed. Run from the repository root
in a fresh virtual environment; do not reuse global packages or old build outputs.

```powershell
py -3.13 -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
pip install -r requirements-build.txt
python -m pytest -q
pyinstaller client_app.spec
```

The output is `dist/client_app.exe`. `client_app.spec` is the shared build
configuration used by both manual builds and `release.ps1`. Source and assets are
resolved relative to the spec, not a developer's machine path. UPX is disabled so
an optional host installation does not change the build. Matching dependency and
Python versions makes the environment repeatable, not necessarily byte-identical.

Tests mock browser automation; Facebook credentials and downloaded Chromium are
not needed for tests/build. Browser setup for actual use is a separate step.

For publishing, activate the same environment first. Git and an authenticated
GitHub CLI must be on PATH, and the branch must be `main`. Then use the existing
`release.ps1` flow. Build/test failure must never be skipped.

Commit the spec, dependency manifests, assets, local helper modules and tests with
the release source. Do not commit `.venv-build`, `build`, `dist` or credentials.

Reference: [PyInstaller spec files](https://pyinstaller.org/en/stable/spec-files.html).
