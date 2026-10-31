"""Scoring of actual findings against expected findings. Pure, no I/O."""

from collections.abc import Sequence
from dataclasses import dataclass

from carbon_preaudit.domain.models import Finding, FindingField

from .cases import ExpectedFinding

FIELDS: tuple[FindingField, ...] = (
    "project_area_ha",
    "tco2e_gross",
    "tco2e_net",
    "buffer_pct",
    "methodology",
)


@dataclass(frozen=True)
class Counts:
    """Confusion counts with derived metrics. A metric is None when its denominator is 0."""

    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    def __add__(self, other: Counts) -> Counts:
        return Counts(self.tp + other.tp, self.fp + other.fp, self.fn + other.fn)


@dataclass(frozen=True)
class CaseScore:
    """Result of matching one case: hits are (expected, actual) pairs."""

    hits: tuple[tuple[ExpectedFinding, Finding], ...]
    misses: tuple[ExpectedFinding, ...]  # expected, no match (FN)
    extras: tuple[Finding, ...]  # actual, no match (FP)

    @property
    def passed(self) -> bool:
        return not self.misses and not self.extras


@dataclass(frozen=True)
class DiagnosisScore:
    """Diagnoses, counted separately from field/severity hits."""

    expected: int = 0  # expected findings that carry a diagnosis
    correct: int = 0  # ... whose matched finding carries the same diagnosis
    unexpected: int = 0  # actual diagnoses that were not expected (or not matched correctly)

    def __add__(self, other: DiagnosisScore) -> DiagnosisScore:
        return DiagnosisScore(
            self.expected + other.expected,
            self.correct + other.correct,
            self.unexpected + other.unexpected,
        )


def match_case(expected: Sequence[ExpectedFinding], actual: Sequence[Finding]) -> CaseScore:
    """Match 1:1 on field and severity; each actual finding serves at most one expectation.

    Known limit: with several findings of the same (field, severity) but different diagnoses the
    greedy pairing may cross them and count diagnoses as wrong although a fitting pairing exists.
    compare() yields at most one finding per field, so this does not occur in practice.
    """
    remaining = list(actual)
    hits: list[tuple[ExpectedFinding, Finding]] = []
    misses: list[ExpectedFinding] = []
    for exp in expected:
        found = next(
            (f for f in remaining if f.field == exp.field and f.severity == exp.severity), None
        )
        if found is None:
            misses.append(exp)
        else:
            remaining.remove(found)
            hits.append((exp, found))
    return CaseScore(tuple(hits), tuple(misses), tuple(remaining))


def field_counts(score: CaseScore) -> dict[FindingField, Counts]:
    """TP, FP, FN of one case per field. A wrong severity counts as one FP and one FN."""
    result: dict[FindingField, Counts] = {f: Counts() for f in FIELDS}
    for exp, _ in score.hits:
        result[exp.field] += Counts(tp=1)
    for exp in score.misses:
        result[exp.field] += Counts(fn=1)
    for finding in score.extras:
        result[finding.field] += Counts(fp=1)
    return result


def diagnosis_score(score: CaseScore) -> DiagnosisScore:
    """Count diagnoses of one case."""
    expected = sum(1 for exp, _ in score.hits if exp.diagnosis is not None)
    expected += sum(1 for exp in score.misses if exp.diagnosis is not None)
    correct = sum(
        1 for exp, act in score.hits if exp.diagnosis is not None and exp.diagnosis == act.diagnosis
    )
    unexpected = sum(
        1 for exp, act in score.hits if act.diagnosis is not None and act.diagnosis != exp.diagnosis
    )
    unexpected += sum(1 for f in score.extras if f.diagnosis is not None)
    return DiagnosisScore(expected, correct, unexpected)


@dataclass(frozen=True)
class Totals:
    """Aggregated scores over all scored cases."""

    per_field: dict[FindingField, Counts]
    overall: Counts
    diagnoses: DiagnosisScore


def aggregate(scores: Sequence[CaseScore]) -> Totals:
    """Sum the per-case scores."""
    per_field: dict[FindingField, Counts] = {f: Counts() for f in FIELDS}
    diagnoses = DiagnosisScore()
    for score in scores:
        for field, counts in field_counts(score).items():
            per_field[field] += counts
        diagnoses += diagnosis_score(score)
    overall = Counts()
    for counts in per_field.values():
        overall += counts
    return Totals(per_field, overall, diagnoses)
