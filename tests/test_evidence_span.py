from carbon_preaudit.domain.models import ClaimedValue, ClaimedValues
from carbon_preaudit.preaudit.compare import compare, evidence_span
from tests.test_compare import RUN

TEXT = "Buffer is 120 % of gross. A share of 20 % of gross is withheld."


def test_span_skips_occurrence_inside_a_longer_number() -> None:
    # "20 % of gross" first occurs at index 11 ("1[20 % of gross]"), without a boundary.
    # The evidence is the second occurrence: the text up to "A share of " is 36 chars.
    span = evidence_span("20 % of gross", TEXT)
    assert span is not None
    start, end = span
    assert start == TEXT.index("A share of ") + len("A share of ")
    assert TEXT[start:end] == "20 % of gross"


def test_span_none_without_evidence() -> None:
    assert evidence_span("0 ha total", "Area is 100.0 ha total") is None
    assert evidence_span("two words", TEXT) is None  # too short and absent
    assert evidence_span("20 %", TEXT) is None  # fewer than three words


def test_span_maps_back_over_line_breaks() -> None:
    text = "x\nThe net removals\n  amount to 6,691 tCO2e.\ny"
    span = evidence_span("The net removals amount to 6,691 tCO2e.", text)
    assert span is not None
    assert text[span[0] : span[1]] == "The net removals\n  amount to 6,691 tCO2e."


def test_compare_counts_the_boundary_occurrence() -> None:
    # Unchanged behaviour: 20 % matches the run's buffer of 20 %, so no finding.
    claimed = ClaimedValues(
        buffer_pct=ClaimedValue[float](value=20.0, quote="20 % of gross"),
    )
    findings = compare(claimed, RUN, TEXT)
    assert [f.field for f in findings if f.field == "buffer_pct"] == []
