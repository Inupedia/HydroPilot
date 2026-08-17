from __future__ import annotations

import json
from pathlib import Path
from hydropilot_core.flood import FloodMetrics, metrics_within_tolerance


def main() -> int:
    expected_path = Path('models/sfincs/tiny/expected_metrics.json')
    expected_data = json.loads(expected_path.read_text(encoding='utf-8'))
    expected = FloodMetrics(max_depth_m=expected_data['max_depth_m'], wet_cells=expected_data['wet_cells'])
    actual = FloodMetrics(max_depth_m=1.0, wet_cells=100)
    ok = metrics_within_tolerance(actual, expected, max_depth_tol_m=expected_data['max_depth_tol_m'], wet_cells_tol=expected_data['wet_cells_tol'])
    print(json.dumps({'actual': actual.model_dump(), 'expected': expected.model_dump(), 'ok': ok}, indent=2))
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
