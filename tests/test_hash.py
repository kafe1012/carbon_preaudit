import pytest
from helpers import CSV_HEADER, SQUARE_001, polygon_text

from carbon_preaudit.calc import params, version
from carbon_preaudit.calc.hashing import run_hash
from carbon_preaudit.calc.inputs import parse_inputs

GEO = polygon_text(SQUARE_001)
ROWS = ["P1,400,T1,20,15,0.6", "P1,400,T2,12.5,9,", "P2,400,T1,18,14,0.55"]


def _hash(rows: list[str] = ROWS, buffer_pct: float = 20.0, geo: str = GEO) -> str:
    return run_hash(parse_inputs(geo, CSV_HEADER + "\n".join(rows) + "\n", buffer_pct))


def test_hash_ignores_row_order() -> None:
    assert _hash(list(reversed(ROWS))) == _hash()


def test_hash_ignores_number_format() -> None:
    other = ["P1,400.0,T1,20.0,15.0,0.60", "P1,4e2,T2,12.5,9.0,", "P2,400,T1,18,14,0.55"]
    assert _hash(other) == _hash()


def test_hash_changes_with_buffer_pct() -> None:
    assert _hash(buffer_pct=15.0) != _hash()


def test_hash_changes_with_polygon_and_trees() -> None:
    assert _hash(geo=polygon_text([[0, 0], [0.02, 0], [0.02, 0.02], [0, 0.02], [0, 0]])) != _hash()
    assert _hash([ROWS[0], ROWS[1], "P2,400,T1,18,14,0.56"]) != _hash()


def test_hash_distinguishes_missing_density_from_default() -> None:
    explicit = [ROWS[0], "P1,400,T2,12.5,9,0.6", ROWS[2]]
    assert _hash(explicit) != _hash()


def test_hash_changes_with_params_version(monkeypatch: pytest.MonkeyPatch) -> None:
    before = _hash()
    monkeypatch.setattr(params, "PARAMS_VERSION", "999")
    assert _hash() != before


def test_hash_changes_with_calc_version(monkeypatch: pytest.MonkeyPatch) -> None:
    before = _hash()
    monkeypatch.setattr(version, "CALC_VERSION", "999")
    assert _hash() != before


def test_hash_normalizes_negative_zero() -> None:
    plain = polygon_text([[0, 0], [0.01, 0], [0.01, 0.01], [0, 0.01], [0, 0]])
    negative = polygon_text([[-0.0, 0], [0.01, 0], [0.01, 0.01], [0, 0.01], [-0.0, 0]])
    assert _hash(geo=negative) == _hash(geo=plain)
    assert _hash(buffer_pct=-0.0) == _hash(buffer_pct=0.0)


def test_hash_follows_polygon_as_delivered() -> None:
    # ADR 0002: ring start and altitude are part of what is (or is not) hashed
    rotated = polygon_text([[0.01, 0], [0.01, 0.01], [0, 0.01], [0, 0], [0.01, 0]])
    assert _hash(geo=rotated) != _hash()
    with_altitude = polygon_text(
        [[0, 0, 5], [0.01, 0, 5], [0.01, 0.01, 5], [0, 0.01, 5], [0, 0, 5]]
    )
    assert _hash(geo=with_altitude) == _hash()
