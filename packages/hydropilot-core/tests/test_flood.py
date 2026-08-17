from pathlib import Path
from hydropilot_core.flood import FloodMetrics, FloodModelAdapter, FloodModelRun, metrics_within_tolerance


def test_sfincs_docker_command_is_deterministic():
    command = FloodModelAdapter().build_docker_command(FloodModelRun(model_dir=Path('/tmp/model'), image='deltares/sfincs-cpu:v2.2.1'))
    assert command == ['docker', 'run', '--rm', '-v', '/tmp/model:/data', '-w', '/data', 'deltares/sfincs-cpu:v2.2.1', 'sfincs']


def test_flood_metrics_tolerance():
    assert metrics_within_tolerance(FloodMetrics(max_depth_m=1.02, wet_cells=101), FloodMetrics(max_depth_m=1.0, wet_cells=100), max_depth_tol_m=0.05, wet_cells_tol=2)
