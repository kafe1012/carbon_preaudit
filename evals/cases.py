"""Loading and validating eval cases (YAML)."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from carbon_preaudit.domain.models import Diagnosis, FindingField, Severity

DEFAULT_CASES_DIR = Path(__file__).parent / "cases"


class CaseError(Exception):
    """An eval case file is unreadable or invalid."""


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ExpectedFinding(_Frozen):
    """A finding the case is expected to produce."""

    field: FindingField
    severity: Severity
    diagnosis: Diagnosis | None = None


class Case(_Frozen):
    """One eval case: a PDD text and the findings it should produce."""

    id: str = Field(min_length=1)
    description: str
    text: str = Field(min_length=1)
    expected: tuple[ExpectedFinding, ...]


def load_case(path: Path) -> Case:
    """Load one case file."""
    try:
        raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as e:
        raise CaseError(f"{path.name}: cannot be read: {e}") from e
    try:
        return Case.model_validate(raw)
    except ValidationError as e:
        raise CaseError(f"{path.name}: invalid case: {e}") from e


def load_cases(directory: Path = DEFAULT_CASES_DIR) -> list[Case]:
    """Load all `*.yaml` cases of a directory, sorted by file name. Ids must be unique."""
    if not directory.is_dir():
        raise CaseError(f"{directory}: not a directory")
    cases = [load_case(p) for p in sorted(directory.glob("*.yaml"))]
    ids = [c.id for c in cases]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise CaseError(f"duplicate case ids: {', '.join(duplicates)}")
    return cases
