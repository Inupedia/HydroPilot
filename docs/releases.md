# Desktop releases

HydroPilot desktop releases are created from version tags.

A pushed tag matching `v*` triggers `.github/workflows/release.yml`. The workflow:

1. derives the Electron package version from the tag;
2. builds the FastAPI sidecar with PyInstaller on each native runner;
3. packages the Vue/Cesium renderer with Electron Builder;
4. uploads build artifacts from macOS Apple Silicon, macOS Intel, Windows x64, and Linux x64;
5. creates a GitHub Release with generated release notes and attaches all installers.

Example:

```bash
git tag v0.2.0
git push origin v0.2.0
```

Release assets are expected to include native macOS DMG/ZIP builds, Windows NSIS/ZIP builds, and Linux AppImage/TAR.GZ builds.

Code signing and Apple notarization are intentionally separate from the unsigned V0.2 packaging baseline and can be added through repository secrets without changing the runtime architecture.
