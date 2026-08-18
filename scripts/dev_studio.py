from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def terminate(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None: return
    process.terminate()
    try: process.wait(timeout=5)
    except subprocess.TimeoutExpired: process.kill()

def main() -> int:
    npm = shutil.which("npm")
    if npm is None:
        print("npm was not found. Install Node.js 22+ first.", file=sys.stderr)
        return 2
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "apps" / "api" / "src"), str(ROOT / "packages" / "hydropilot-core" / "src"), env.get("PYTHONPATH", "")])
    api = subprocess.Popen([sys.executable,"-m","uvicorn","hydropilot_api.main:app","--reload","--host","127.0.0.1","--port","8000"], cwd=ROOT, env=env)
    web = subprocess.Popen([npm,"run","dev:vite"], cwd=ROOT / "apps" / "studio", env=env)
    print("HydroPilot React/Tauri development services started:\n  UI:       http://127.0.0.1:5173\n  API:      http://127.0.0.1:8000\n  API docs: http://127.0.0.1:8000/docs")
    try:
        while True:
            if api.poll() is not None: return api.returncode or 1
            if web.poll() is not None: return web.returncode or 1
            time.sleep(0.25)
    except KeyboardInterrupt: return 0
    finally:
        terminate(web); terminate(api)
if __name__ == "__main__": raise SystemExit(main())
