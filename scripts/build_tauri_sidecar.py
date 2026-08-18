from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "build" / "tauri-sidecar"
DIST_DIR = BUILD_ROOT / "dist"
WORK_DIR = BUILD_ROOT / "work"
SPEC_DIR = BUILD_ROOT / "spec"


def rust_target_triple() -> str:
    rustc = shutil.which("rustc")
    if rustc is None:
        raise SystemExit("rustc was not found. Install the Rust toolchain required by Tauri.")
    output = subprocess.check_output([rustc, "-vV"], text=True)
    for line in output.splitlines():
        if line.startswith("host: "):
            return line.split(":", 1)[1].strip()
    raise SystemExit("Could not determine the Rust host target triple")


def main() -> int:
    try:
        import PyInstaller.__main__  # type: ignore
    except ImportError:
        print("PyInstaller is required. Run `python -m pip install pyinstaller`.", file=sys.stderr)
        return 2

    for directory in (DIST_DIR, WORK_DIR, SPEC_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    PyInstaller.__main__.run([
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        "hydropilot-api",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(WORK_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--paths",
        str(ROOT / "apps" / "api" / "src"),
        "--paths",
        str(ROOT / "packages" / "hydropilot-core" / "src"),
        str(ROOT / "apps" / "api" / "desktop_entry.py"),
    ])

    triple = rust_target_triple()
    suffix = ".exe" if os.name == "nt" else ""
    source = DIST_DIR / f"hydropilot-api{suffix}"
    target_dir = ROOT / "apps" / "studio" / "src-tauri" / "binaries"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"hydropilot-api-{triple}{suffix}"
    if not source.exists():
        raise SystemExit(f"PyInstaller output not found: {source}")
    shutil.copy2(source, target)
    if os.name != "nt":
        target.chmod(0o755)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
