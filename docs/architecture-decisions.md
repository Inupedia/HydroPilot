# Architecture decisions

## ADR-002: Provider registry plus adapter families

HydroPilot represents vendor identity separately from request protocol. This avoids one implementation per vendor and keeps future GIS-agent orchestration provider-neutral.

## ADR-003: Releases are built natively per operating system

The FastAPI sidecar is compiled with PyInstaller, so release binaries are built on native GitHub Actions runners rather than cross-compiled. macOS Apple Silicon and Intel are separate release targets.
