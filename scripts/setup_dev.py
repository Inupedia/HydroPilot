from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    npm = shutil.which("npm")
    if npm is None:
        print("npm was not found. Install Node.js 22+ first.", file=sys.stderr)
        return 2

    run([
        sys.executable,
        "-m",
        "pip",
        "install",
        "-e",
        "packages/hydropilot-core",
        "-e",
        "apps/api",
    ])
    run([npm, "install"], cwd=ROOT / "apps" / "web")
    run([npm, "install"], cwd=ROOT / "apps" / "desktop")

    print("\nHydroPilot development dependencies are ready.")
    print("Run `npm run dev` for the complete Electron + FastAPI + Vue/Cesium stack.")
    print("Run `npm run dev:web` for FastAPI + browser Vite mode without Electron.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
