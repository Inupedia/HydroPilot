from __future__ import annotations

import os

import uvicorn

from hydropilot_api.main import app


def main() -> None:
    host = os.getenv("HYDROPILOT_API_HOST", "127.0.0.1")
    port = int(os.getenv("HYDROPILOT_API_PORT", "43817"))
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv("HYDROPILOT_API_LOG_LEVEL", "warning"),
        access_log=False,
    )


if __name__ == "__main__":
    main()
