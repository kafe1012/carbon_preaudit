"""Parse GeoJSON and CSV text into validated ProjectInputs."""

import csv
import io
import json
import math
import unicodedata
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from carbon_preaudit.calc.params import DEFAULT_BUFFER_PCT, MAX_WOOD_DENSITY_G_CM3
from carbon_preaudit.domain.models import GeoJSONPolygon, Plot, ProjectInputs, Tree

_Coord = Annotated[float, Field(allow_inf_nan=False)]

REQUIRED_COLUMNS = ("plot_id", "plot_area_m2", "tree_id", "dbh_cm", "height_m")


class InputError(Exception):
    """Base class for invalid project inputs."""


class InvalidGeoJSONError(InputError):
    """The GeoJSON text is not valid JSON or not a well-formed polygon."""


class UnsupportedGeometryError(InputError):
    """The geometry is not a plain Polygon (Feature, FeatureCollection, MultiPolygon, ...)."""


class OpenRingError(InputError):
    """A polygon ring is not closed or has fewer than 4 positions."""


class InvalidGeometryError(InputError):
    """The polygon is geometrically invalid (range, degenerate, self-intersecting, bad holes)."""


class MissingColumnError(InputError):
    """A required CSV column is missing."""


class EmptyPlotsError(InputError):
    """The CSV contains no tree rows, so there is no plot."""


class InvalidValueError(InputError):
    """A value is not a finite number, not positive, or out of range."""


class InconsistentPlotAreaError(InputError):
    """Rows of one plot disagree on plot_area_m2."""


class DuplicateTreeError(InputError):
    """A tree_id occurs more than once within a plot."""


class _RawPolygon(BaseModel):
    """Raw GeoJSON Polygon as delivered: positions are [lon, lat] or [lon, lat, altitude]."""

    model_config = ConfigDict(strict=True)

    type: str
    coordinates: list[list[Annotated[list[_Coord], Field(min_length=2, max_length=3)]]] = Field(
        min_length=1
    )


_ENVELOPE: TypeAdapter[dict[str, object]] = TypeAdapter(dict[str, object])

type _Point = tuple[float, float]


def _cross(o: _Point, a: _Point, b: _Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _on_box(a: _Point, b: _Point, c: _Point) -> bool:
    """Return True if c lies within the bounding box of a and b (c collinear with a, b)."""
    return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])


def _segments_intersect(p1: _Point, p2: _Point, p3: _Point, p4: _Point) -> bool:
    """Return True if segment p1-p2 touches or crosses segment p3-p4 (planar lon/lat)."""
    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)
    if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
        return True
    return (
        (d1 == 0 and _on_box(p3, p4, p1))
        or (d2 == 0 and _on_box(p3, p4, p2))
        or (d3 == 0 and _on_box(p1, p2, p3))
        or (d4 == 0 and _on_box(p1, p2, p4))
    )


def _check_ring_geometry(ring: list[_Point]) -> None:
    for lon, lat in ring:
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise InvalidGeometryError(
                f"Position [{lon}, {lat}] is outside lon [-180, 180] / lat [-90, 90]"
            )
    if len(set(ring)) < 3:
        raise InvalidGeometryError("Polygon ring needs at least 3 distinct points")
    n = len(ring) - 1  # number of segments
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue  # neighbours share an end point
            if _segments_intersect(ring[i], ring[i + 1], ring[j], ring[j + 1]):
                raise InvalidGeometryError(f"Polygon ring intersects itself (segments {i} and {j})")


def _parse_polygon(geojson_text: str) -> GeoJSONPolygon:
    try:
        data: object = json.loads(geojson_text)
    except json.JSONDecodeError as exc:
        raise InvalidGeoJSONError(f"GeoJSON is not valid JSON: {exc}") from exc
    try:
        envelope = _ENVELOPE.validate_python(data)
    except ValidationError as exc:
        raise InvalidGeoJSONError("GeoJSON must be a JSON object") from exc
    geo_type = envelope.get("type")
    if geo_type != "Polygon":
        raise UnsupportedGeometryError(
            f"Only a plain GeoJSON Polygon is supported, got {geo_type!r}; "
            "Feature, FeatureCollection and MultiPolygon are rejected."
        )
    try:
        raw = _RawPolygon.model_validate(envelope)
    except ValidationError as exc:
        raise InvalidGeoJSONError(
            "Polygon needs 'coordinates' as rings of [lon, lat] positions with finite numbers"
        ) from exc
    rings: list[list[_Point]] = [[(pos[0], pos[1]) for pos in ring] for ring in raw.coordinates]
    for ring in rings:
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise OpenRingError("Polygon rings must be closed and have at least 4 positions")
        _check_ring_geometry(ring)
    return GeoJSONPolygon.model_validate({"type": "Polygon", "coordinates": rings})


def _number(raw: str, column: str, line: int) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise InvalidValueError(f"Line {line}: {column}={raw!r} is not a number") from exc
    if not math.isfinite(value) or value <= 0:
        raise InvalidValueError(f"Line {line}: {column}={raw!r} must be a finite number > 0")
    return value


def _id(raw: str | None) -> str:
    return unicodedata.normalize("NFC", raw or "").strip()


def _parse_plots(csv_text: str) -> tuple[Plot, ...]:
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    header = [name.strip() for name in reader.fieldnames or []]
    reader.fieldnames = header
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise MissingColumnError(f"Missing CSV columns: {', '.join(missing)}")
    areas: dict[str, float] = {}
    trees: dict[str, dict[str, Tree]] = {}
    for row in reader:
        line = reader.line_num
        if None in row:
            raise InvalidValueError(
                f"Line {line}: too many fields (decimal comma? use a decimal point)"
            )
        if any(v is None for v in row.values()):
            raise InvalidValueError(f"Line {line}: too few fields")
        plot_id = _id(row["plot_id"])
        tree_id = _id(row["tree_id"])
        if not plot_id or not tree_id:
            raise InvalidValueError(f"Line {line}: plot_id and tree_id must not be empty")
        area = _number((row["plot_area_m2"] or "").strip(), "plot_area_m2", line)
        if areas.setdefault(plot_id, area) != area:
            raise InconsistentPlotAreaError(
                f"Line {line}: plot {plot_id} has conflicting plot_area_m2 "
                f"({areas[plot_id]} vs {area})"
            )
        raw_rho = (row.get("wood_density") or "").strip()
        rho = _number(raw_rho, "wood_density", line) if raw_rho else None
        if rho is not None and rho > MAX_WOOD_DENSITY_G_CM3:
            raise InvalidValueError(
                f"Line {line}: wood_density={raw_rho!r} exceeds {MAX_WOOD_DENSITY_G_CM3}; "
                "g/cm3 expected (not kg/m3)"
            )
        tree = Tree(
            plot_id=plot_id,
            tree_id=tree_id,
            dbh_cm=_number((row["dbh_cm"] or "").strip(), "dbh_cm", line),
            height_m=_number((row["height_m"] or "").strip(), "height_m", line),
            wood_density_g_cm3=rho,
        )
        plot_trees = trees.setdefault(plot_id, {})
        if tree_id in plot_trees:
            raise DuplicateTreeError(f"Line {line}: duplicate tree_id {tree_id} in plot {plot_id}")
        plot_trees[tree_id] = tree
    if not trees:
        raise EmptyPlotsError("CSV contains no tree rows")
    return tuple(
        Plot(
            plot_id=pid,
            plot_area_m2=areas[pid],
            trees=tuple(plot_trees[tid] for tid in sorted(plot_trees)),
        )
        for pid, plot_trees in sorted(trees.items())
    )


def parse_inputs(
    geojson_text: str, csv_text: str, buffer_pct: float = DEFAULT_BUFFER_PCT
) -> ProjectInputs:
    """Parse and validate GeoJSON and CSV text. Plots and trees are sorted by id."""
    if not math.isfinite(buffer_pct) or not 0 <= buffer_pct <= 100:
        raise InvalidValueError(f"buffer_pct={buffer_pct!r} must be between 0 and 100")
    return ProjectInputs(
        polygon=_parse_polygon(geojson_text),
        plots=_parse_plots(csv_text),
        buffer_pct=buffer_pct,
    )
