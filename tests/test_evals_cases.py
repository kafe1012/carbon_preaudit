from pathlib import Path

import pytest

from carbon_preaudit.domain.models import Diagnosis, Severity
from evals.cases import CaseError, load_case, load_cases

VALID = """\
id: demo-01
description: demo
text: |
  The project area covers 500.0 ha.
expected:
  - field: tco2e_net
    severity: critical
    diagnosis: tc_instead_of_tco2e
  - field: project_area_ha
    severity: major
"""


def write(directory: Path, name: str, content: str) -> Path:
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def test_load_valid_case(tmp_path: Path) -> None:
    case = load_case(write(tmp_path, "a.yaml", VALID))
    assert case.id == "demo-01"
    assert case.expected[0].severity is Severity.CRITICAL
    assert case.expected[0].diagnosis is Diagnosis.TC_INSTEAD_OF_TCO2E
    assert case.expected[1].diagnosis is None


def test_empty_expected_is_valid(tmp_path: Path) -> None:
    content = VALID.split("expected:")[0] + "expected: []\n"
    assert load_case(write(tmp_path, "a.yaml", content)).expected == ()


@pytest.mark.parametrize(
    "content",
    [
        VALID.replace("severity: major", "severity: huge"),  # invalid value
        VALID + "extra: 1\n",  # unknown key
        "id: [unclosed\n",  # broken YAML
    ],
)
def test_invalid_case_raises(tmp_path: Path, content: str) -> None:
    with pytest.raises(CaseError):
        load_case(write(tmp_path, "a.yaml", content))


def test_load_cases_sorted_and_unique(tmp_path: Path) -> None:
    write(tmp_path, "b.yaml", VALID.replace("demo-01", "b"))
    write(tmp_path, "a.yaml", VALID.replace("demo-01", "a"))
    assert [c.id for c in load_cases(tmp_path)] == ["a", "b"]
    write(tmp_path, "c.yaml", VALID.replace("demo-01", "a"))
    with pytest.raises(CaseError, match="duplicate"):
        load_cases(tmp_path)


def test_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(CaseError):
        load_cases(tmp_path / "nope")
