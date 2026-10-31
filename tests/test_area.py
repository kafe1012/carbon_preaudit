import math

import pytest

from carbon_preaudit.calc.area import polygon_area_ha
from carbon_preaudit.domain.models import GeoJSONPolygon


def _square(lon0: float, lat0: float, size: float) -> list[list[float]]:
    return [
        [lon0, lat0],
        [lon0 + size, lat0],
        [lon0 + size, lat0 + size],
        [lon0, lat0 + size],
        [lon0, lat0],
    ]


def _poly(*rings: list[list[float]]) -> GeoJSONPolygon:
    return GeoJSONPolygon.model_validate({"type": "Polygon", "coordinates": list(rings)})


# Independent reference: at the equator a small cell of d degrees has the area
#   (d_rad * M) * (d_rad * N) with M = a (1 - e^2) (meridian radius) and N = a (prime vertical),
# a = 6378137 m, e^2 = 0.00669437999014 (WGS84). d = 0.01 deg:
#   d_rad = 1.745329e-4; M = 6335439.327 m; N = 6378137 m
#   area = 3.046174e-8 * 6335439.327 * 6378137 = 1 230 907 m2 = 123.09 ha
_A = 6378137.0
_E2 = 0.00669437999014
_D_RAD = math.radians(0.01)
CELL_HA = (_D_RAD * _A * (1 - _E2)) * (_D_RAD * _A) / 10_000


def test_small_square_at_equator() -> None:
    assert polygon_area_ha(_poly(_square(0, 0, 0.01))) == pytest.approx(CELL_HA, rel=1e-4)
    assert pytest.approx(123.09, rel=1e-4) == CELL_HA


def test_orientation_does_not_matter() -> None:
    ring = _square(0, 0, 0.01)[::-1]
    assert polygon_area_ha(_poly(ring)) == pytest.approx(CELL_HA, rel=1e-4)


def test_polygon_with_hole() -> None:
    # 0.02 deg outer square = 4 cells, 0.01 deg hole = 1 cell -> 3 cells
    outer = _square(0, 0, 0.02)
    hole = _square(0.005, 0.005, 0.01)
    assert polygon_area_ha(_poly(outer, hole)) == pytest.approx(3 * CELL_HA, rel=1e-4)
