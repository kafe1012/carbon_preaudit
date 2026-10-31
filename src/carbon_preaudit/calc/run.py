"""The calculation run (plan 01, steps 1-7). No rounding internally."""

import math

from carbon_preaudit.calc import params, version
from carbon_preaudit.calc.allometry import agb_kg, tco2e_from_agb_kg
from carbon_preaudit.calc.area import M2_PER_HA, polygon_area_ha
from carbon_preaudit.calc.hashing import run_hash
from carbon_preaudit.calc.inputs import InvalidValueError
from carbon_preaudit.domain.models import CalculationRun, PlotResult, ProjectInputs


def calculate(inputs: ProjectInputs) -> CalculationRun:
    """Compute gross, buffer and net tCO2e for the project."""
    default_count = 0
    plot_results: list[PlotResult] = []
    for plot in inputs.plots:
        plot_agb = 0.0
        for tree in plot.trees:
            rho = tree.wood_density_g_cm3
            if rho is None:
                rho = params.DEFAULT_WOOD_DENSITY_G_CM3
                default_count += 1
            try:
                plot_agb += agb_kg(rho, tree.dbh_cm, tree.height_m)
            except OverflowError as exc:
                raise InvalidValueError(
                    f"Tree {tree.tree_id} in plot {plot.plot_id}: values too large to compute"
                ) from exc
        plot_results.append(
            PlotResult(
                plot_id=plot.plot_id,
                plot_area_ha=plot.plot_area_m2 / M2_PER_HA,
                agb_kg=plot_agb,
                tco2e=tco2e_from_agb_kg(plot_agb),
            )
        )
    total_tco2e = sum(p.tco2e for p in plot_results)
    total_area_ha = sum(p.plot_area_ha for p in plot_results)
    tco2e_per_ha = total_tco2e / total_area_ha
    if not math.isfinite(tco2e_per_ha):
        raise InvalidValueError("Result is not finite; tree values are implausibly large")
    project_area_ha = polygon_area_ha(inputs.polygon)
    gross = tco2e_per_ha * project_area_ha
    buffer = gross * inputs.buffer_pct / 100
    return CalculationRun(
        run_hash=run_hash(inputs),
        params_version=params.PARAMS_VERSION,
        calc_version=version.CALC_VERSION,
        project_area_ha=project_area_ha,
        plot_count=len(inputs.plots),
        tree_count=sum(len(p.trees) for p in inputs.plots),
        trees_with_default_density=default_count,
        tco2e_per_ha=tco2e_per_ha,
        tco2e_gross=gross,
        buffer_pct=inputs.buffer_pct,
        tco2e_buffer=buffer,
        tco2e_net=gross - buffer,
        plots=tuple(plot_results),
    )
