from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field


class FloodModelRun(BaseModel):
    model_dir: Path
    image: str = "deltares/sfincs-cpu:latest"
    timeout_seconds: int = Field(default=300, gt=0)


class FloodMetrics(BaseModel):
    max_depth_m: float = Field(ge=0)
    wet_cells: int = Field(ge=0)


class FloodModelAdapter:
    def build_docker_command(self, run: FloodModelRun) -> list[str]:
        model_dir = run.model_dir.resolve()
        return ["docker", "run", "--rm", "-v", f"{model_dir}:/data", "-w", "/data", run.image, "sfincs"]


def metrics_within_tolerance(actual: FloodMetrics, expected: FloodMetrics, *, max_depth_tol_m: float, wet_cells_tol: int) -> bool:
    return abs(actual.max_depth_m - expected.max_depth_m) <= max_depth_tol_m and abs(actual.wet_cells - expected.wet_cells) <= wet_cells_tol
