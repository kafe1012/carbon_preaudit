import json
import math
import unicodedata

import pytest
from helpers import CSV_HEADER, ONE_TREE_CSV, SQUARE_001, polygon_text
from pydantic import ValidationError

from carbon_preaudit.calc.inputs import (
    DuplicateTreeError,
    EmptyPlotsError,
    InconsistentPlotAreaError,
    InputError,
    InvalidGeoJSONError,
    InvalidGeometryError,
    InvalidValueError,
    MissingColumnError,
    OpenRingError,
    UnsupportedGeometryError,
    parse_inputs,
)
from carbon_preaudit.calc.run import calculate
from carbon_preaudit.domain.models import (
    CalculationRun,
    GeoJSONPolygon,
    Plot,
    PlotResult,
    ProjectInputs,
    Tree,
)

GEO = polygon_text(SQUARE_001)


def test_valid_inputs_are_sorted_and_typed() -> None:
    csv_text = CSV_HEADER + "B,400,T2,10,8,\nB,400,T1,10,8,0.5\nA,400,T1,10,8,0.5\n"
    inputs = parse_inputs(GEO, csv_text)
    assert [p.plot_id for p in inputs.plots] == ["A", "B"]
    assert [t.tree_id for t in inputs.plots[1].trees] == ["T1", "T2"]
    assert inputs.plots[1].trees[1].wood_density_g_cm3 is None
    assert inputs.buffer_pct == 20.0


def test_feature_is_rejected() -> None:
    feature = {"type": "Feature", "properties": {}, "geometry": json.loads(GEO)}
    with pytest.raises(UnsupportedGeometryError, match="Feature"):
        parse_inputs(json.dumps(feature), ONE_TREE_CSV)


def test_feature_collection_is_rejected() -> None:
    fc = {"type": "FeatureCollection", "features": []}
    with pytest.raises(UnsupportedGeometryError):
        parse_inputs(json.dumps(fc), ONE_TREE_CSV)


def test_multipolygon_is_rejected() -> None:
    mp = {"type": "MultiPolygon", "coordinates": [[SQUARE_001]]}
    with pytest.raises(UnsupportedGeometryError, match="MultiPolygon"):
        parse_inputs(json.dumps(mp), ONE_TREE_CSV)


def test_open_ring_is_rejected() -> None:
    with pytest.raises(OpenRingError):
        parse_inputs(polygon_text(SQUARE_001[:-1]), ONE_TREE_CSV)


@pytest.mark.parametrize("text", ["not json", "[1, 2]", '{"type": "Polygon"}'])
def test_malformed_geojson_is_rejected(text: str) -> None:
    with pytest.raises(InvalidGeoJSONError):
        parse_inputs(text, ONE_TREE_CSV)


def test_bad_position_is_rejected() -> None:
    with pytest.raises(InvalidGeoJSONError):
        parse_inputs(polygon_text([[0, 0], [1], [1, 1], [0, 0]]), ONE_TREE_CSV)


def test_csv_without_rows_is_rejected() -> None:
    with pytest.raises(EmptyPlotsError):
        parse_inputs(GEO, CSV_HEADER)


def test_plot_model_rejects_empty_tree_list() -> None:
    with pytest.raises(ValidationError):
        Plot(plot_id="P1", plot_area_m2=400.0, trees=())


def test_conflicting_plot_area_is_rejected() -> None:
    csv_text = CSV_HEADER + "P1,400,T1,10,8,0.5\nP1,500,T2,10,8,0.5\n"
    with pytest.raises(InconsistentPlotAreaError):
        parse_inputs(GEO, csv_text)


def test_duplicate_tree_id_in_plot_is_rejected() -> None:
    csv_text = CSV_HEADER + "P1,400,T1,10,8,0.5\nP1,400,T1,11,9,0.5\n"
    with pytest.raises(DuplicateTreeError):
        parse_inputs(GEO, csv_text)


def test_same_tree_id_in_different_plots_is_allowed() -> None:
    csv_text = CSV_HEADER + "P1,400,T1,10,8,0.5\nP2,400,T1,11,9,0.5\n"
    assert len(parse_inputs(GEO, csv_text).plots) == 2


@pytest.mark.parametrize(
    "row",
    [
        "P1,0,T1,10,8,0.5",
        "P1,-400,T1,10,8,0.5",
        "P1,400,T1,0,8,0.5",
        "P1,400,T1,10,-1,0.5",
        "P1,400,T1,10,8,0",
        "P1,400,T1,10,8,-0.5",
        "P1,400,T1,abc,8,0.5",
        "P1,400,T1,nan,8,0.5",
        "P1,400,T1,inf,8,0.5",
        "P1,,T1,10,8,0.5",
        ",400,T1,10,8,0.5",
    ],
)
def test_invalid_numbers_are_rejected(row: str) -> None:
    with pytest.raises(InvalidValueError):
        parse_inputs(GEO, CSV_HEADER + row + "\n")


@pytest.mark.parametrize("column", ["plot_id", "plot_area_m2", "tree_id", "dbh_cm", "height_m"])
def test_missing_column_is_rejected(column: str) -> None:
    cols = [c for c in CSV_HEADER.strip().split(",") if c != column]
    with pytest.raises(MissingColumnError, match=column):
        parse_inputs(GEO, ",".join(cols) + "\n")


@pytest.mark.parametrize("buffer_pct", [-1.0, 100.5, float("nan")])
def test_buffer_out_of_range_is_rejected(buffer_pct: float) -> None:
    with pytest.raises(InvalidValueError):
        parse_inputs(GEO, ONE_TREE_CSV, buffer_pct)


def test_all_errors_share_base_class() -> None:
    with pytest.raises(InputError):
        parse_inputs("nope", ONE_TREE_CSV)


# --- K1: geometry validation -------------------------------------------------------------------


def _calc(ring_a: list[list[float]], *holes: list[list[float]]) -> CalculationRun:
    return calculate(parse_inputs(polygon_text(ring_a, *holes), ONE_TREE_CSV))


@pytest.mark.parametrize(
    "ring",
    [
        [[0, 90], [1, 90], [1, 95], [0, 95], [0, 90]],
        [[0, -95], [1, -95], [1, -90], [0, -90], [0, -95]],
        [[400, 0], [400.01, 0], [400.01, 0.01], [400, 0.01], [400, 0]],
        [[-181, 0], [-180, 0], [-180, 1], [-181, 1], [-181, 0]],
    ],
)
def test_coordinates_out_of_range_are_rejected(ring: list[list[float]]) -> None:
    with pytest.raises(InvalidGeometryError):
        parse_inputs(polygon_text(ring), ONE_TREE_CSV)


def test_degenerate_ring_is_rejected() -> None:
    with pytest.raises(InvalidGeometryError, match="distinct"):
        parse_inputs(polygon_text([[0, 0], [1, 1], [0, 0], [0, 0]]), ONE_TREE_CSV)


@pytest.mark.parametrize(
    "ring",
    [
        [[0, 0], [0.01, 0.01], [0.01, 0], [0, 0.01], [0, 0]],  # symmetric bow tie
        [[0, 0], [0.02, 0.01], [0.02, 0], [0, 0.01], [0, 0]],  # asymmetric bow tie
        [[0, 0], [0.02, 0], [0.02, 0.02], [0.01, 0], [0.01, 0.02], [0, 0.02], [0, 0]],  # touch
    ],
)
def test_self_intersecting_ring_is_rejected(ring: list[list[float]]) -> None:
    with pytest.raises(InvalidGeometryError, match="intersects itself"):
        parse_inputs(polygon_text(ring), ONE_TREE_CSV)


def test_self_intersecting_hole_is_rejected() -> None:
    bow_tie = [[0.002, 0.002], [0.004, 0.004], [0.004, 0.002], [0.002, 0.004], [0.002, 0.002]]
    with pytest.raises(InvalidGeometryError, match="intersects itself"):
        parse_inputs(polygon_text(SQUARE_001, bow_tie), ONE_TREE_CSV)


def test_concave_ring_is_accepted() -> None:
    l_shape = [[0, 0], [0.02, 0], [0.02, 0.01], [0.01, 0.01], [0.01, 0.02], [0, 0.02], [0, 0]]
    assert _calc(l_shape).project_area_ha > 0


def test_hole_larger_than_outer_ring_is_rejected() -> None:
    big = [[-0.01, -0.01], [0.02, -0.01], [0.02, 0.02], [-0.01, 0.02], [-0.01, -0.01]]
    with pytest.raises(InvalidGeometryError, match="hole"):
        _calc(SQUARE_001, big)


def test_hole_reduces_area() -> None:
    hole = [[0.002, 0.002], [0.004, 0.002], [0.004, 0.004], [0.002, 0.004], [0.002, 0.002]]
    assert _calc(SQUARE_001, hole).project_area_ha < _calc(SQUARE_001).project_area_ha


def test_extreme_coordinate_is_input_error() -> None:
    ring: list[list[float]] = [[10**400, 0], [1, 0], [1, 1], [0, 1], [10**400, 0]]
    with pytest.raises(InputError):
        parse_inputs(polygon_text(ring), ONE_TREE_CSV)


@pytest.mark.parametrize("bad", [True, "1", None])
def test_non_numeric_coordinate_is_rejected(bad: object) -> None:
    ring = [[bad, 0], [1, 0], [1, 1], [0, 1], [bad, 0]]
    with pytest.raises(InvalidGeoJSONError):
        parse_inputs(json.dumps({"type": "Polygon", "coordinates": [ring]}), ONE_TREE_CSV)


def test_nan_coordinate_is_rejected() -> None:
    text = '{"type": "Polygon", "coordinates": [[[NaN, 0], [1, 0], [1, 1], [0, 1], [NaN, 0]]]}'
    with pytest.raises(InvalidGeoJSONError):
        parse_inputs(text, ONE_TREE_CSV)


def test_altitude_is_dropped() -> None:
    ring = [[0, 0, 5], [0.01, 0, 5], [0.01, 0.01, 5], [0, 0.01, 5], [0, 0, 5]]
    assert parse_inputs(polygon_text(ring), ONE_TREE_CSV).polygon.coordinates[0][0] == (0.0, 0.0)


def test_models_reject_non_finite_floats() -> None:
    kwargs = {
        "run_hash": "x",
        "params_version": "1",
        "calc_version": "1",
        "project_area_ha": 1.0,
        "plot_count": 1,
        "tree_count": 1,
        "trees_with_default_density": 0,
        "tco2e_per_ha": 1.0,
        "tco2e_gross": 1.0,
        "buffer_pct": 20.0,
        "tco2e_buffer": 0.2,
        "tco2e_net": 0.8,
        "plots": (),
    }
    CalculationRun(**kwargs)  # pyright: ignore[reportArgumentType]
    for field in (
        "project_area_ha",
        "tco2e_per_ha",
        "tco2e_gross",
        "buffer_pct",
        "tco2e_buffer",
        "tco2e_net",
    ):
        for bad in (math.nan, math.inf):
            with pytest.raises(ValidationError):
                CalculationRun(**{**kwargs, field: bad})  # pyright: ignore[reportArgumentType]
    for field in ("plot_area_ha", "agb_kg", "tco2e"):
        values = {"plot_id": "P", "plot_area_ha": 1.0, "agb_kg": 1.0, "tco2e": 1.0}
        with pytest.raises(ValidationError):
            PlotResult(**{**values, field: math.nan})  # pyright: ignore[reportArgumentType]


def test_polygon_model_rejects_nan_and_range() -> None:
    nan_ring = [[math.nan, 0], [1, 0], [1, 1], [0, 1], [math.nan, 0]]
    with pytest.raises(ValidationError):
        GeoJSONPolygon.model_validate({"type": "Polygon", "coordinates": [nan_ring]})
    far = [[0, 90], [1, 90], [1, 95], [0, 95], [0, 90]]
    with pytest.raises(ValidationError):
        GeoJSONPolygon.model_validate({"type": "Polygon", "coordinates": [far]})


def test_overflow_in_calculation_is_input_error() -> None:
    csv_text = CSV_HEADER + "P1,400,T1,1e200,15,0.6\n"
    with pytest.raises(InvalidValueError, match="too large"):
        calculate(parse_inputs(GEO, csv_text))


def test_huge_but_representable_values_are_input_error() -> None:
    csv_text = CSV_HEADER + "P1,1e-300,T1,1e100,1e100,0.6\n"
    with pytest.raises(InvalidValueError):
        calculate(parse_inputs(GEO, csv_text))


# --- W1: field counts ---------------------------------------------------------------------------


def test_too_many_fields_is_rejected_with_line_number() -> None:
    # decimal comma: "12,5" and "0,6" split into extra fields
    with pytest.raises(InvalidValueError, match=r"Line 2: too many fields"):
        parse_inputs(GEO, CSV_HEADER + "P1,400,T1,12,5,15,0,6\n")


def test_oversized_csv_field_raises_input_error() -> None:
    # A field above the csv module's 128 KiB limit raises csv.Error, not an InputError.
    row = "P1,400," + "x" * 140_000 + ",20,15,0.6\n"
    with pytest.raises(InvalidValueError, match=r"CSV could not be read"):
        parse_inputs(GEO, CSV_HEADER + row)


def test_too_few_fields_is_rejected_with_line_number() -> None:
    with pytest.raises(InvalidValueError, match=r"Line 3: too few fields"):
        parse_inputs(GEO, ONE_TREE_CSV + "P1,400,T2,20\n")


# --- W2: wood density unit ----------------------------------------------------------------------


def test_wood_density_in_kg_per_m3_is_rejected() -> None:
    with pytest.raises(InvalidValueError, match=r"g/cm3"):
        parse_inputs(GEO, CSV_HEADER + "P1,400,T1,20,15,600\n")


def test_wood_density_at_upper_bound_is_accepted() -> None:
    inputs = parse_inputs(GEO, CSV_HEADER + "P1,400,T1,20,15,1.5\n")
    assert inputs.plots[0].trees[0].wood_density_g_cm3 == 1.5
    with pytest.raises(ValidationError):
        Tree(plot_id="P", tree_id="T", dbh_cm=1, height_m=1, wood_density_g_cm3=1.51)


# --- W3: model invariants ------------------------------------------------------------------------


def _tree(plot_id: str = "P", tree_id: str = "T") -> Tree:
    return Tree(plot_id=plot_id, tree_id=tree_id, dbh_cm=20, height_m=15)


def test_plot_rejects_duplicate_tree_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        Plot(plot_id="P", plot_area_m2=400, trees=(_tree(), _tree()))


def test_plot_rejects_tree_with_foreign_plot_id() -> None:
    with pytest.raises(ValidationError, match="expected"):
        Plot(plot_id="P", plot_area_m2=400, trees=(_tree("X"),))


def test_project_inputs_reject_duplicate_plot_ids() -> None:
    polygon = parse_inputs(GEO, ONE_TREE_CSV).polygon
    a = Plot(plot_id="P", plot_area_m2=400, trees=(_tree(),))
    b = Plot(plot_id="P", plot_area_m2=800, trees=(_tree(),))
    with pytest.raises(ValidationError, match="unique"):
        ProjectInputs(polygon=polygon, plots=(a, b))


# --- H3, H4, H6 ----------------------------------------------------------------------------------


def test_ids_are_unicode_normalized_to_nfc() -> None:
    nfc = unicodedata.normalize("NFC", "P\u00e9")
    nfd = unicodedata.normalize("NFD", "P\u00e9")
    assert nfc != nfd
    a = parse_inputs(GEO, CSV_HEADER + f"{nfc},400,T1,20,15,0.6\n")
    b = parse_inputs(GEO, CSV_HEADER + f"{nfd},400,T1,20,15,0.6\n")
    assert a == b
    assert a.plots[0].plot_id == nfc


def test_bom_is_removed() -> None:
    inputs = parse_inputs(GEO, "\ufeff" + ONE_TREE_CSV)
    assert inputs.plots[0].plot_id == "P1"


def test_header_names_are_trimmed() -> None:
    header = "plot_id, plot_area_m2, tree_id, dbh_cm, height_m, wood_density\n"
    assert parse_inputs(GEO, header + "P1,400,T1,20,15,0.6\n") == parse_inputs(GEO, ONE_TREE_CSV)


def test_empty_tree_id_is_rejected() -> None:
    with pytest.raises(InvalidValueError, match="tree_id"):
        parse_inputs(GEO, CSV_HEADER + "P1,400,,20,15,0.6\n")


def test_plot_without_trees_row_is_rejected() -> None:
    with pytest.raises(InvalidValueError):
        parse_inputs(GEO, CSV_HEADER + "P3,400,,,,\n")
