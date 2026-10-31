from carbon_preaudit.domain.models import Diagnosis, Finding, FindingField, Severity
from evals.cases import ExpectedFinding
from evals.scorer import Counts, aggregate, match_case


def finding(field: FindingField, severity: Severity, diagnosis: Diagnosis | None = None) -> Finding:
    return Finding(
        field=field,
        severity=severity,
        claimed=1.0,
        computed=2.0,
        quote="q",
        diagnosis=diagnosis,
        message="m",
    )


def expected(
    field: FindingField, severity: Severity, diagnosis: Diagnosis | None = None
) -> ExpectedFinding:
    return ExpectedFinding(field=field, severity=severity, diagnosis=diagnosis)


def test_perfect_match() -> None:
    score = match_case(
        [expected("project_area_ha", Severity.MAJOR)],
        [finding("project_area_ha", Severity.MAJOR)],
    )
    totals = aggregate([score])
    assert score.passed
    assert totals.per_field["project_area_ha"] == Counts(tp=1)
    assert totals.per_field["project_area_ha"].precision == 1.0
    assert totals.per_field["project_area_ha"].recall == 1.0
    assert totals.overall == Counts(tp=1)


def test_extra_finding_is_false_positive() -> None:
    score = match_case([], [finding("buffer_pct", Severity.MAJOR)])
    totals = aggregate([score])
    assert not score.passed
    assert totals.per_field["buffer_pct"] == Counts(fp=1)
    assert totals.per_field["buffer_pct"].precision == 0.0
    assert totals.per_field["buffer_pct"].recall is None


def test_missing_finding_is_false_negative() -> None:
    score = match_case([expected("tco2e_net", Severity.CRITICAL)], [])
    totals = aggregate([score])
    assert totals.per_field["tco2e_net"] == Counts(fn=1)
    assert totals.per_field["tco2e_net"].recall == 0.0
    assert totals.per_field["tco2e_net"].precision is None


def test_wrong_severity_counts_as_fp_and_fn() -> None:
    score = match_case(
        [expected("tco2e_net", Severity.CRITICAL)], [finding("tco2e_net", Severity.INFO)]
    )
    assert aggregate([score]).per_field["tco2e_net"] == Counts(fp=1, fn=1)


def test_matching_is_one_to_one() -> None:
    score = match_case(
        [expected("buffer_pct", Severity.MAJOR), expected("buffer_pct", Severity.MAJOR)],
        [finding("buffer_pct", Severity.MAJOR)],
    )
    assert aggregate([score]).per_field["buffer_pct"] == Counts(tp=1, fn=1)


def test_zero_over_zero_is_none() -> None:
    totals = aggregate([match_case([], [])])
    assert totals.per_field["methodology"].precision is None
    assert totals.per_field["methodology"].recall is None
    assert totals.overall.precision is None


def test_correct_diagnosis() -> None:
    diag = Diagnosis.TC_INSTEAD_OF_TCO2E
    score = match_case(
        [expected("tco2e_net", Severity.CRITICAL, diag)],
        [finding("tco2e_net", Severity.CRITICAL, diag)],
    )
    d = aggregate([score]).diagnoses
    assert (d.expected, d.correct, d.unexpected) == (1, 1, 0)


def test_wrong_or_missing_diagnosis() -> None:
    wrong = match_case(
        [expected("tco2e_net", Severity.CRITICAL, Diagnosis.TC_INSTEAD_OF_TCO2E)],
        [finding("tco2e_net", Severity.CRITICAL, Diagnosis.GROSS_NET_SWAPPED)],
    )
    d = aggregate([wrong]).diagnoses
    assert (d.expected, d.correct, d.unexpected) == (1, 0, 1)
    none = match_case(
        [expected("tco2e_net", Severity.CRITICAL, Diagnosis.GROSS_NET_SWAPPED)],
        [finding("tco2e_net", Severity.CRITICAL)],
    )
    d = aggregate([none]).diagnoses
    assert (d.expected, d.correct, d.unexpected) == (1, 0, 0)


def test_unexpected_diagnosis() -> None:
    score = match_case(
        [expected("tco2e_net", Severity.CRITICAL)],
        [finding("tco2e_net", Severity.CRITICAL, Diagnosis.GROSS_NET_SWAPPED)],
    )
    d = aggregate([score]).diagnoses
    assert (d.expected, d.correct, d.unexpected) == (0, 0, 1)


def test_aggregate_sums_cases() -> None:
    a = match_case(
        [expected("buffer_pct", Severity.MAJOR)], [finding("buffer_pct", Severity.MAJOR)]
    )
    b = match_case([], [finding("buffer_pct", Severity.MAJOR)])
    counts = aggregate([a, b]).per_field["buffer_pct"]
    assert counts == Counts(tp=1, fp=1)
    assert counts.precision == 0.5


def test_missed_expectation_with_diagnosis_counts_as_expected() -> None:
    # Expected tco2e_net/critical + diagnosis, actual finding has another severity: a miss.
    score = match_case(
        [expected("tco2e_net", Severity.CRITICAL, Diagnosis.GROSS_NET_SWAPPED)],
        [],
    )
    assert len(score.misses) == 1
    d = aggregate([score]).diagnoses
    assert (d.expected, d.correct, d.unexpected) == (1, 0, 0)


def test_extra_finding_with_diagnosis_counts_as_unexpected() -> None:
    score = match_case(
        [],
        [finding("tco2e_net", Severity.CRITICAL, Diagnosis.TC_INSTEAD_OF_TCO2E)],
    )
    assert len(score.extras) == 1
    d = aggregate([score]).diagnoses
    assert (d.expected, d.correct, d.unexpected) == (0, 0, 1)
