import pytest
from helpers import CSV_HEADER, ONE_TREE_CSV, SQUARE_001, polygon_text

from carbon_preaudit.calc import params
from carbon_preaudit.calc.allometry import agb_kg, tco2e_from_agb_kg
from carbon_preaudit.calc.hashing import canonical_json
from carbon_preaudit.calc.inputs import parse_inputs
from carbon_preaudit.calc.run import calculate
from carbon_preaudit.calc.version import CALC_VERSION

# Golden values per CALC_VERSION (ADR 0002). A logic change must add a new version entry.
#
# Hand calculation (one tree, D = 20 cm, H = 15 m, rho = 0.6 g/cm3, plot 400 m2):
#   rho * D^2 * H = 0.6 * 400 * 15 = 3600
#   ln(3600) = 8.18869; * 0.976 = 7.99216; exp(7.99216) = 2957.6
#   AGB = 0.0673 * 2957.6 = 199.05 kg   (exact: 199.0518897259263)
#   tCO2e = 199.0519 / 1000 * 0.47 * 44/12 = 0.19905 * 1.72333 = 0.34303
#   plot area = 400 / 10000 = 0.04 ha -> 0.34303 / 0.04 = 8.5758 tCO2e/ha
#
# Project values for the same tree and the 0.01 deg square at the equator (SQUARE_001):
#   area = 123.0907 ha (small-cell formula in test_area.py)
#   gross = 8.57582 tCO2e/ha * 123.0907 ha = 1055.60 tCO2e
#   net = 1055.60 * (1 - 20/100) = 844.48 tCO2e
#   run_hash = SHA-256 of the canonical JSON in test_canonical_json_golden (a snapshot).
# Existing entries in GOLDEN and PARAMS_GOLDEN are never changed (ADR 0002).
GOLDEN = {
    "1": {
        "project_area_ha": 123.09072049932536,
        "tco2e_gross": 1055.6037292042702,
        "tco2e_net": 844.4829833634161,
        "run_hash": "2b71559ad8a2c596d197d884e8dc77b80aee0e03a34309bcc38a73d7ab1da9aa",
        "agb_kg": 199.0518897259263,
        "tco2e": 0.3430327566276796,
        "tco2e_per_ha": 8.57581891569199,
    },
}

# Snapshot of every value in params.py per PARAMS_VERSION (ADR 0002).
PARAMS_GOLDEN: dict[str, dict[str, float | str]] = {
    "1": {
        "CHAVE_A": 0.0673,
        "CHAVE_B": 0.976,
        "CARBON_FRACTION": 0.47,
        "CO2_PER_C": 44 / 12,
        "DEFAULT_WOOD_DENSITY_G_CM3": 0.6,
        "MAX_WOOD_DENSITY_G_CM3": 1.5,
        "DEFAULT_BUFFER_PCT": 20.0,
        "TOL_AREA_REL": 0.01,
        "TOL_TONNES_REL": 0.02,
        "TOL_BUFFER_ABS": 0.01,
        "EXPECTED_METHODOLOGY": "VM0047",
    },
}
REL = 1e-9


def test_params_golden_entry_exists_for_current_params_version() -> None:
    assert params.PARAMS_VERSION in PARAMS_GOLDEN, (
        f"no PARAMS_GOLDEN entry for PARAMS_VERSION {params.PARAMS_VERSION!r}"
    )


def test_params_match_golden_for_current_params_version() -> None:
    current: dict[str, float | str] = {
        name: value
        for name, value in vars(params).items()
        if name.isupper() and name != "PARAMS_VERSION"
    }
    assert current == PARAMS_GOLDEN[params.PARAMS_VERSION]


def test_canonical_json_golden() -> None:
    expected = (
        '{"buffer_pct":20.0,"calc_version":"1","params_version":"1",'
        '"polygon":[[[0.0,0.0],[0.01,0.0],[0.01,0.01],[0.0,0.01],[0.0,0.0]]],'
        '"trees":[{"dbh_cm":20.0,"height_m":15.0,"plot_area_m2":400.0,"plot_id":"P1",'
        '"tree_id":"T1","wood_density_g_cm3":0.6}]}'
    )
    assert canonical_json(parse_inputs(polygon_text(SQUARE_001), ONE_TREE_CSV)) == expected


def test_golden_entry_exists_for_current_calc_version() -> None:
    assert CALC_VERSION in GOLDEN, f"no GOLDEN entry for CALC_VERSION {CALC_VERSION!r}"


def test_allometry_golden() -> None:
    golden = GOLDEN[CALC_VERSION]
    agb = agb_kg(0.6, 20.0, 15.0)
    assert agb == pytest.approx(golden["agb_kg"], rel=REL)
    assert agb == pytest.approx(199.05, rel=1e-4)
    assert tco2e_from_agb_kg(agb) == pytest.approx(golden["tco2e"], rel=REL)


def test_run_golden_one_tree_one_plot() -> None:
    golden = GOLDEN[CALC_VERSION]
    run = calculate(parse_inputs(polygon_text(SQUARE_001), ONE_TREE_CSV))
    assert run.calc_version == CALC_VERSION
    assert run.plot_count == 1
    assert run.tree_count == 1
    assert run.plots[0].agb_kg == pytest.approx(golden["agb_kg"], rel=REL)
    assert run.plots[0].tco2e == pytest.approx(golden["tco2e"], rel=REL)
    assert run.plots[0].plot_area_ha == pytest.approx(0.04)
    assert run.tco2e_per_ha == pytest.approx(golden["tco2e_per_ha"], rel=REL)
    assert run.project_area_ha == pytest.approx(golden["project_area_ha"], rel=REL)
    assert run.tco2e_gross == pytest.approx(golden["tco2e_gross"], rel=REL)
    assert run.tco2e_buffer == pytest.approx(golden["tco2e_gross"] * 0.2, rel=REL)
    assert run.tco2e_net == pytest.approx(golden["tco2e_net"], rel=REL)
    assert run.run_hash == golden["run_hash"]


def test_area_weighted_across_plots() -> None:
    # Plot A 400 m2 with the golden tree, plot B 800 m2 with the same tree twice:
    # sum tCO2e = 3 * 0.34303 = 1.02910, sum area = 0.12 ha -> 8.5758 tCO2e/ha
    csv_text = CSV_HEADER + "A,400,T1,20,15,0.6\n" + "B,800,T1,20,15,0.6\n" + "B,800,T2,20,15,0.6\n"
    run = calculate(parse_inputs(polygon_text(SQUARE_001), csv_text))
    assert run.tco2e_per_ha == pytest.approx(GOLDEN[CALC_VERSION]["tco2e_per_ha"], rel=REL)


def test_default_density_is_counted_and_applied() -> None:
    csv_text = CSV_HEADER + "P1,400,T1,20,15,\n" + "P1,400,T2,20,15,0.6\n" + "P1,400,T3,20,15,0.7\n"
    run = calculate(parse_inputs(polygon_text(SQUARE_001), csv_text))
    assert run.tree_count == 3
    assert run.trees_with_default_density == 1
    expected = agb_kg(0.6, 20, 15) * 2 + agb_kg(0.7, 20, 15)
    assert run.plots[0].agb_kg == pytest.approx(expected, rel=REL)


def test_wood_density_column_may_be_absent() -> None:
    csv_text = "plot_id,plot_area_m2,tree_id,dbh_cm,height_m\nP1,400,T1,20,15\n"
    run = calculate(parse_inputs(polygon_text(SQUARE_001), csv_text))
    assert run.trees_with_default_density == 1
    assert run.plots[0].agb_kg == pytest.approx(GOLDEN[CALC_VERSION]["agb_kg"], rel=REL)
