from carbon_preaudit.domain.models import ClaimedValue, ClaimedValues, Finding, Severity
from carbon_preaudit.preaudit.compare import squash, squash_with_offsets
from carbon_preaudit.web.highlight import (
    Mark,
    build_marks,
    highlight,
)


def test_text_is_escaped_before_marking() -> None:
    text = 'Intro <script>alert("x")</script> The area is 100 ha & more.'
    out = str(highlight(text, [Mark("The area is 100 ha & more.", "major", "Fläche")]))
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert '<mark class="hl hl-major" title="Fläche">The area is 100 ha &amp; more.</mark>' in out


def test_quote_with_html_is_escaped_inside_the_mark() -> None:
    text = "See <b>the area is 100 ha</b> here"
    out = str(highlight(text, [Mark("<b>the area is 100 ha</b>", "ok", "Fläche")]))
    assert "<b>" not in out
    assert "&lt;b&gt;the area is 100 ha&lt;/b&gt;</mark>" in out


def test_quote_across_line_break_marks_original_text() -> None:
    text = "First sentence.\nThe net removals\n  amount to 6,691 tCO2e.\nLast."
    out = str(highlight(text, [Mark("The net removals amount to 6,691 tCO2e.", "ok", "Netto")]))
    assert (
        '<mark class="hl hl-ok" title="Netto">The net removals\n  amount to 6,691 tCO2e.</mark>'
        in out
    )
    assert out.startswith("First sentence.\n<mark")
    assert out.endswith("</mark>\nLast.")


def test_quote_not_in_text_is_not_marked() -> None:
    text = "The area covers 100 ha of land."
    out = highlight(text, [Mark("The area covers 200 ha of land.", "critical", "Fläche")])
    assert str(out) == text
    assert "<mark" not in out


def test_overlap_keeps_the_more_severe_mark() -> None:
    text = "Gross removals are 8,364 tCO2e in total."
    marks = [
        Mark("Gross removals are 8,364 tCO2e", "ok", "a"),
        Mark("removals are 8,364 tCO2e in total.", "critical", "b"),
    ]
    out = str(highlight(text, marks))
    assert out.count("<mark") == 1
    assert "hl-critical" in out
    assert "Gross " in out.split("<mark")[0]


def test_offsets_agree_with_compare_squash() -> None:
    text = "  a\tb \u00a0c\n\nd  "
    squashed, offsets = squash_with_offsets(text)
    assert squashed == squash(text) == "a b c d"
    assert len(offsets) == len(squashed)


def test_build_marks_levels_follow_findings() -> None:
    claimed = ClaimedValues(
        project_area_ha=ClaimedValue[float](value=100.0, quote="The area covers 100.0 ha."),
        tco2e_gross=ClaimedValue[float](value=1.0, quote="Gross is 1 tCO2e here."),
    )
    finding = Finding(
        field="tco2e_gross",
        severity=Severity.CRITICAL,
        claimed=1.0,
        computed=2.0,
        quote="Gross is 1 tCO2e here.",
        message="x",
    )
    marks = build_marks(claimed, [finding])
    assert [(m.quote, m.level) for m in marks] == [
        ("The area covers 100.0 ha.", "ok"),
        ("Gross is 1 tCO2e here.", "critical"),
    ]


def test_evidence_mark_sits_where_compare_counts_it() -> None:
    # "20 % of gross" first occurs inside "120 % of gross" (no word boundary, no evidence);
    # compare counts the second occurrence, and that one is marked.
    text = "Buffer is 120 % of gross. A share of 20 % of gross is withheld."
    out = str(highlight(text, [Mark("20 % of gross", "ok", "Puffer")]))
    assert "Buffer is 120 % of gross." in out
    assert 'title="Puffer">20 % of gross</mark> is withheld' in out
    assert out.count("<mark") == 1


def test_shared_quote_carries_both_labels() -> None:
    text = "Gross is 100 tCO2e and net is 80 tCO2e overall."
    quote = "Gross is 100 tCO2e and net is 80 tCO2e overall."
    marks = [Mark(quote, "ok", "Brutto"), Mark(quote, "critical", "Netto")]
    out = str(highlight(text, marks))
    assert out.count("<mark") == 1
    assert 'class="hl hl-critical" title="Netto, Brutto"' in out
