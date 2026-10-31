"""Canonical JSON and run hash (ADR 0002)."""

import hashlib
import json

from carbon_preaudit.calc import params, version
from carbon_preaudit.domain.models import ProjectInputs

type JsonValue = str | float | int | list[JsonValue] | dict[str, JsonValue] | None


def _f(x: float) -> float:
    """Return x as float; -0.0 becomes 0.0 so it hashes like 0.0."""
    return float(x) + 0.0


def canonical_payload(inputs: ProjectInputs) -> dict[str, JsonValue]:
    """Build the hashed payload. Trees are sorted by (plot_id, tree_id)."""
    trees = sorted(
        (
            (plot.plot_id, t.tree_id, plot.plot_area_m2, t)
            for plot in inputs.plots
            for t in plot.trees
        ),
        key=lambda x: (x[0], x[1]),
    )
    tree_entries: list[JsonValue] = [
        {
            "plot_id": plot_id,
            "tree_id": tree_id,
            "plot_area_m2": _f(area),
            "dbh_cm": _f(t.dbh_cm),
            "height_m": _f(t.height_m),
            "wood_density_g_cm3": None
            if t.wood_density_g_cm3 is None
            else _f(t.wood_density_g_cm3),
        }
        for plot_id, tree_id, area, t in trees
    ]
    rings: list[JsonValue] = [
        [[_f(p[0]), _f(p[1])] for p in ring] for ring in inputs.polygon.coordinates
    ]
    return {
        "polygon": rings,
        "trees": tree_entries,
        "buffer_pct": _f(inputs.buffer_pct),
        "params_version": params.PARAMS_VERSION,
        "calc_version": version.CALC_VERSION,
    }


def canonical_json(inputs: ProjectInputs) -> str:
    """Return the canonical JSON string of the inputs and versions."""
    return json.dumps(
        canonical_payload(inputs), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def run_hash(inputs: ProjectInputs) -> str:
    """Return the SHA-256 hex digest over the canonical JSON."""
    return hashlib.sha256(canonical_json(inputs).encode("utf-8")).hexdigest()
