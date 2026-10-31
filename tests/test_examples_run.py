from pathlib import Path

import pytest

from carbon_preaudit.calc.inputs import parse_inputs
from carbon_preaudit.calc.run import calculate

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_run_over_examples_is_plausible() -> None:
    inputs = parse_inputs(
        (EXAMPLES / "project.geojson").read_text(encoding="utf-8"),
        (EXAMPLES / "plots.csv").read_text(encoding="utf-8"),
    )
    run = calculate(inputs)
    assert run.project_area_ha == pytest.approx(100, rel=0.05)
    assert run.plot_count == 3
    assert run.tree_count == 30
    assert run.trees_with_default_density == 2
    assert 50 < run.tco2e_per_ha < 150
    assert run.tco2e_gross == pytest.approx(run.tco2e_per_ha * run.project_area_ha)
    assert run.tco2e_net == pytest.approx(run.tco2e_gross * 0.8)
    assert run.tco2e_net + run.tco2e_buffer == pytest.approx(run.tco2e_gross)
    assert calculate(inputs).run_hash == run.run_hash
