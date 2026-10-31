"""The rules for a quote as evidence, tested once here; compare and highlight use evidence_span."""

import pytest

from carbon_preaudit.preaudit.compare import evidence_span


def test_whitespace_is_normalized_and_the_span_maps_back() -> None:
    text = "A share of 20 %\n  of the gross\N{NO-BREAK SPACE}removals\N{NARROW NO-BREAK SPACE}is"
    span = evidence_span("A share of 20 % of the gross removals", text)
    assert span is not None
    assert text[span[0] : span[1]] == "A share of 20 %\n  of the gross\N{NO-BREAK SPACE}removals"


def test_occurrence_inside_a_longer_number_is_skipped() -> None:
    text = "Buffer is 120 % of gross. A share of 20 % of gross is withheld."
    span = evidence_span("20 % of gross", text)
    assert span is not None
    assert span[0] == text.index("A share of ") + len("A share of ")


@pytest.mark.parametrize(
    ("quote", "text"),
    [
        ("20 %", "A share of 20 % is withheld."),  # fewer than three words
        ("0 ha of", "The project covers 100.0 ha of land."),  # starts inside a number
        ("project covers 100.0 hect", "The project covers 100.0 hectares."),  # ends inside a word
        ("a share of 20 %", "A share of 20 % is withheld."),  # wording must match exactly
        ("two words only", "Nothing like it here."),  # not in the text
    ],
)
def test_no_evidence(quote: str, text: str) -> None:
    assert evidence_span(quote, text) is None
