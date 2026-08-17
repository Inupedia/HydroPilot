from __future__ import annotations

import os
import shutil
from pathlib import Path


root = Path(__file__).resolve().parents[1]
source = root / "dist" / ("hydropilot-api.exe" if os.name == "nt" else "hydropilot-api")
target_dir = root / "apps" / "desktop" / "resources" / "api"
target_dir.mkdir(parents=True, exist_ok=True)
target = target_dir / source.name

if not source.exists():
    raise SystemExit(f"PyInstaller output not found: {source}")

shutil.copy2(source, target)
if os.name != "nt":
    target.chmod(0o755)

print(target)
