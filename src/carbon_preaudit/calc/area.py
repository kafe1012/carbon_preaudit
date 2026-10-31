"""Geodetic polygon area."""

import math

from pyproj import Geod

from carbon_preaudit.calc.inputs import InvalidGeometryError
from carbon_preaudit.domain.models import GeoJSONPolygon, Ring

M2_PER_HA = 10_000.0
_GEOD = Geod(ellps="WGS84")


def _ring_area_m2(ring: Ring) -> float:
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    area, _perimeter = _GEOD.polygon_area_perimeter(lons, lats)  # pyright: ignore[reportUnknownMemberType]
    return abs(float(area))


def polygon_area_ha(polygon: GeoJSONPolygon) -> float:
    """Return the geodetic area in ha: outer ring minus holes (WGS84 ellipsoid)."""
    outer, *holes = polygon.coordinates
    outer_m2 = _ring_area_m2(outer)
    hole_m2 = [_ring_area_m2(h) for h in holes]
    if any(h >= outer_m2 for h in hole_m2):
        raise InvalidGeometryError("A hole must be smaller than the outer ring")
    area_ha = (outer_m2 - sum(hole_m2)) / M2_PER_HA
    if not math.isfinite(area_ha) or area_ha <= 0:
        raise InvalidGeometryError(f"Polygon area must be finite and > 0 ha, got {area_ha}")
    return area_ha
