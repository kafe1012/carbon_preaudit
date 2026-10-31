from pathlib import Path

import pytest

from carbon_preaudit.calc.params import CO2_PER_C
from carbon_preaudit.domain.models import (
    CalculationRun,
    ClaimedValue,
    ClaimedValues,
    Diagnosis,
    Finding,
    Severity,
)
from carbon_preaudit.preaudit.compare import compare, number_candidates, number_format

EXAMPLES = Path(__file__).parent.parent / "examples"

# Hand-made run with round numbers: tolerance borders are exact in floating point.
RUN = CalculationRun(
    run_hash="h",
    params_version="1",
    calc_version="1",
    project_area_ha=100.0,
    plot_count=1,
    tree_count=1,
    trees_with_default_density=0,
    tco2e_per_ha=10.0,
    tco2e_gross=1000.0,
    buffer_pct=20.0,
    tco2e_buffer=200.0,
    tco2e_net=800.0,
    plots=(),
)


def q(quote: str) -> str:
    """Pad short quotes to the minimum word count so tests of other rules stay focused."""
    return quote if len(quote.split()) >= 3 else f"stated as {quote}"


def num(value: float, quote: str) -> ClaimedValue[float]:
    return ClaimedValue[float](value=value, quote=q(quote))


def meth(value: str, quote: str) -> ClaimedValue[str]:
    return ClaimedValue[str](value=value, quote=q(quote))


def _de(x: float) -> str:
    return f"{x:,.1f}".replace(",", "\0").replace(".", ",").replace("\0", ".")


def present(findings: list[Finding]) -> list[Finding]:
    """Drop the info findings for fields that are missing in the text."""
    return [f for f in findings if f.quote is not None]


def only(field: str, value: float, quote: str) -> ClaimedValues:
    return ClaimedValues.model_validate({field: {"value": value, "quote": q(quote)}})


def run_compare(claimed: ClaimedValues, *, text: str | None = None) -> list[Finding]:
    quotes = [
        cv.quote
        for cv in (
            claimed.project_area_ha,
            claimed.tco2e_gross,
            claimed.tco2e_net,
            claimed.buffer_pct,
            claimed.methodology,
        )
        if cv.quote
    ]
    return present(compare(claimed, RUN, text if text is not None else " . ".join(quotes)))


# (field, claimed value that is computed + tolerance, quote, outside value, severity)
ROWS = [
    ("project_area_ha", 101.0, "101 ha", 101.5, Severity.MAJOR),  # 1/100 = TOL_AREA_REL
    ("tco2e_gross", 1020.0, "1020 tCO2e", 1021.0, Severity.CRITICAL),  # 20/1000 = TOL_TONNES_REL
    ("tco2e_net", 816.0, "816 tCO2e", 817.0, Severity.CRITICAL),  # 16/800 = TOL_TONNES_REL
]


@pytest.mark.parametrize(("field", "border", "quote", "outside", "severity"), ROWS)
def test_numeric_rows_inside_border_outside(
    field: str, border: float, quote: str, outside: float, severity: Severity
) -> None:
    k = getattr(RUN, field)
    # exactly equal: no finding
    assert run_compare(only(field, k, f"{k}")) == []
    # exactly on the tolerance border: still inside
    assert run_compare(only(field, border, quote)) == []
    # outside
    findings = run_compare(only(field, outside, f"{outside}"))
    assert len(findings) == 1
    f = findings[0]
    assert (f.field, f.severity, f.claimed, f.computed) == (field, severity, outside, k)
    assert f.quote == q(f"{outside}")
    assert f.deviation_rel == pytest.approx((outside - k) / k)


def test_all_missing_gives_five_info_findings_in_field_order() -> None:
    findings = compare(ClaimedValues(), RUN, "")
    assert [f.field for f in findings] == [
        "project_area_ha",
        "tco2e_gross",
        "tco2e_net",
        "buffer_pct",
        "methodology",
    ]
    assert {f.severity for f in findings} == {Severity.INFO}
    assert all(f.claimed is None and f.quote is None for f in findings)


def test_buffer_rows() -> None:
    # k = 20.0: equal and on the border (abs_tol 0.01 against rel_tol 1e-9 * 20) are inside
    assert run_compare(ClaimedValues(buffer_pct=num(20.0, "20 %"))) == []
    assert run_compare(ClaimedValues(buffer_pct=num(20.005, "20.005 %"))) == []
    outside = run_compare(ClaimedValues(buffer_pct=num(15.0, "15 %")))
    assert [(f.field, f.severity) for f in outside] == [("buffer_pct", Severity.MAJOR)]
    assert outside[0].claimed == 15.0
    assert outside[0].computed == 20.0


def test_buffer_exact_border_with_zero_buffer() -> None:
    run = RUN.model_copy(update={"buffer_pct": 0.0})
    assert present(compare(ClaimedValues(buffer_pct=num(0.01, "0.01 %")), run, q("0.01 %"))) == []
    findings = present(compare(ClaimedValues(buffer_pct=num(0.02, "0.02 %")), run, q("0.02 %")))
    assert len(findings) == 1
    assert findings[0].deviation_rel is None  # k == 0


def test_zero_computed_value_does_not_divide() -> None:
    run = RUN.model_copy(update={"tco2e_net": 0.0, "buffer_pct": 100.0})
    assert present(compare(ClaimedValues(tco2e_net=num(0.0, "0 t")), run, q("0 t"))) == []
    f = present(compare(ClaimedValues(tco2e_net=num(5.0, "5 t")), run, q("5 t")))
    assert f[0].severity is Severity.CRITICAL
    assert f[0].deviation_rel is None


# --- diagnoses ---


def test_diagnosis_tc_instead_of_tco2e_positive() -> None:
    c = 1000.0 / CO2_PER_C  # 272.73 tC
    findings = run_compare(ClaimedValues(tco2e_gross=num(c, f"{c!r} tC")))
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].diagnosis is Diagnosis.TC_INSTEAD_OF_TCO2E
    assert "tC statt tCO₂e" in findings[0].message
    assert f"behauptet {_de(c)} tC," in findings[0].message  # unit of the claim is tC
    assert "berechnet 1.000,0 tCO₂e" in findings[0].message


def test_diagnosis_tc_tolerance_is_relative_to_comparison_value() -> None:
    base = 1000.0 / CO2_PER_C
    inside = base * 1.019
    outside = base * 1.021
    f_in = run_compare(ClaimedValues(tco2e_gross=num(inside, f"{inside!r} tC")))
    f_out = run_compare(ClaimedValues(tco2e_gross=num(outside, f"{outside!r} tC")))
    assert f_in[0].diagnosis is Diagnosis.TC_INSTEAD_OF_TCO2E
    assert f_out[0].diagnosis is None


def test_diagnosis_tc_on_net() -> None:
    c = 800.0 / CO2_PER_C
    findings = run_compare(ClaimedValues(tco2e_net=num(c, f"{c!r} tC")))
    assert findings[0].diagnosis is Diagnosis.TC_INSTEAD_OF_TCO2E


def test_diagnosis_gross_net_swapped_positive() -> None:
    findings = run_compare(ClaimedValues(tco2e_net=num(1000.0, "1000 t")))
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].diagnosis is Diagnosis.GROSS_NET_SWAPPED
    assert "brutto/netto" in findings[0].message.lower()


def test_diagnosis_gross_net_swapped_border_and_negative() -> None:
    border = run_compare(ClaimedValues(tco2e_net=num(1020.0, "1020 t")))
    assert border[0].diagnosis is Diagnosis.GROSS_NET_SWAPPED
    negative = run_compare(ClaimedValues(tco2e_net=num(1021.0, "1021 t")))
    assert negative[0].diagnosis is None


def test_gross_net_diagnosis_only_for_net_field() -> None:
    # gross claimed 800 (the net value) is a deviation, but not a swap diagnosis
    findings = run_compare(ClaimedValues(tco2e_gross=num(800.0, "800 t")))
    assert findings[0].diagnosis is None


# --- quote check ---


def test_quote_not_in_text_is_info_and_not_compared() -> None:
    claimed = ClaimedValues(tco2e_gross=num(5000.0, "5000 tCO2e gross"))
    findings = present(compare(claimed, RUN, "The text says something else entirely."))
    gross = [f for f in findings if f.field == "tco2e_gross"]
    assert len(gross) == 1
    assert gross[0].severity is Severity.INFO
    assert gross[0].claimed == 5000.0
    assert gross[0].quote == "5000 tCO2e gross"  # three words already
    assert "Zitat nicht im Text" in gross[0].message


# --- value check against the quote ---


@pytest.mark.parametrize(
    ("value", "quote"),
    [
        (8364.0, "8364 tCO2e"),
        (8364.0, "8.364 tCO2e"),  # ambiguous text: both readings count
        (8.364, "8.364 tCO2e"),
        (100.0, "buffer of 20 % applies to the 100 ha"),  # any number of the quote
    ],
)
def test_value_found_in_quote(value: float, quote: str) -> None:
    # use a field where any number is a deviation, so a found value yields a Finding with severity
    # other than info, a missing value yields the info finding
    claim = num(value, quote)
    assert claim.quote is not None
    findings = present(compare(ClaimedValues(tco2e_gross=claim), RUN, claim.quote))
    assert findings
    assert findings[0].severity is Severity.CRITICAL


@pytest.mark.parametrize(
    ("value", "quote"),
    [
        (9000.0, "8,364 tCO2e"),
        (836.4, "8,364 tCO2e"),  # off by a factor of ten
        (8364.0, "no number at all"),
    ],
)
def test_value_not_in_quote_is_info_and_not_compared(value: float, quote: str) -> None:
    claim = num(value, quote)
    assert claim.quote is not None
    findings = present(compare(ClaimedValues(tco2e_gross=claim), RUN, claim.quote))
    assert len(findings) == 1
    assert findings[0].severity is Severity.INFO
    assert findings[0].claimed == value
    assert "Wert nicht im Zitat belegt" in findings[0].message


# --- methodology ---


@pytest.mark.parametrize(
    ("value", "quote"),
    [
        ("VM 0047", "VM 0047"),
        ("vm-0047", "vm-0047"),
    ],
)
def test_methodology_variants_match(value: str, quote: str) -> None:
    claimed = ClaimedValues(methodology=meth(value, f"uses {quote} here"))
    assert run_compare(claimed) == []


def test_methodology_other_code_is_major() -> None:
    findings = run_compare(ClaimedValues(methodology=meth("VM0042", "uses VM0042")))
    assert [(f.field, f.severity) for f in findings] == [("methodology", Severity.MAJOR)]
    assert findings[0].claimed == "VM0042"
    assert findings[0].computed == "VM0047"
    assert findings[0].deviation_rel is None


def test_methodology_without_vm_code_is_major() -> None:
    claimed = ClaimedValues(methodology=meth("Verra ARR methodology", "the Verra ARR methodology"))
    findings = run_compare(claimed)
    assert [(f.field, f.severity) for f in findings] == [("methodology", Severity.MAJOR)]


def test_methodology_value_not_in_quote_is_info() -> None:
    findings = run_compare(ClaimedValues(methodology=meth("VM0047", "uses VM0042")))
    assert [(f.field, f.severity) for f in findings] == [("methodology", Severity.INFO)]
    assert "nicht im Zitat belegt" in findings[0].message


def test_methodology_quote_not_in_text_is_info() -> None:
    claimed = ClaimedValues(methodology=meth("VM0047", "uses VM0047"))
    findings = present(compare(claimed, RUN, "unrelated"))
    assert findings[0].severity is Severity.INFO
    assert "Zitat nicht im Text" in findings[0].message


# --- order and message ---


def test_findings_follow_field_order_and_message_is_german_with_both_values() -> None:
    claimed = ClaimedValues(
        methodology=meth("VM0042", "VM0042"),
        buffer_pct=num(10.0, "10 %"),
        tco2e_gross=num(2000.0, "2000 t"),
        project_area_ha=num(150.0, "150 ha"),
    )
    findings = run_compare(claimed)
    assert [f.field for f in findings] == [
        "project_area_ha",
        "tco2e_gross",
        "buffer_pct",
        "methodology",
    ]
    area = findings[0]
    assert "150,00 ha" in area.message
    assert "100,00 ha" in area.message
    assert "+50,0 %" in area.message
    assert "2.000,0 tCO₂e" in findings[1].message


# --- number candidates (W1, H1, H2) ---


@pytest.mark.parametrize(
    ("quote", "expected"),
    [
        ("20 100 ha", {20100.0}),  # one number, neither 20 nor 100 on its own
        ("year 2023 8 364", {2023.0, 8364.0}),  # 2023 has 4 digits: no thousands head
        ("8\N{NARROW NO-BREAK SPACE}364 t", {8364.0}),
        ("8\n364 t", {8.0, 364.0}),  # a line break is no thousands separator
        ("1.234.567,8 t", {1234567.8}),  # both separators: unambiguous
        ("8.364 t", {8364.0, 8.364}),  # ambiguous: both readings stay
        ("tCO2e VM0047 v2", set()),  # digits touching letters are no numbers
        ("-5 %", {-5.0}),
        ("8,000-9,000 t", {8000.0, 9000.0, 8.0, 9.0}),  # range: both ends, no sign
        ("1.2e4 t", set()),  # scientific notation: no candidate, 12000 is not backed
    ],
)
def test_number_candidates(quote: str, expected: set[float]) -> None:
    assert number_candidates(quote) == expected


def test_grouped_number_does_not_back_its_parts() -> None:
    # text says 20 100 ha; the model read 100: not backed, no finding against k = 100 ha
    claimed = ClaimedValues(project_area_ha=num(100.0, "The area covers 20 100 ha"))
    findings = present(compare(claimed, RUN, "The area covers 20 100 ha"))
    assert [f.severity for f in findings] == [Severity.INFO]
    assert "nicht im Zitat belegt" in findings[0].message
    # reading it correctly is backed and a deviation
    claimed = ClaimedValues(project_area_ha=num(20100.0, "The area covers 20 100 ha"))
    findings = present(compare(claimed, RUN, "The area covers 20 100 ha"))
    assert [f.severity for f in findings] == [Severity.MAJOR]


# --- quote as evidence (W4) ---


def test_single_number_quote_is_too_short() -> None:
    text = "A share of 20 % is withheld."
    claim = ClaimedValue[float](value=20.0, quote="20")
    findings = present(compare(ClaimedValues(tco2e_gross=claim), RUN, text))
    assert [(f.severity, f.field) for f in findings] == [(Severity.INFO, "tco2e_gross")]
    assert "Zitat zu kurz als Beleg" in findings[0].message


def test_quote_not_in_text_stays_not_found_even_if_short() -> None:
    claim = ClaimedValue[float](value=20.0, quote="20")
    findings = present(compare(ClaimedValues(buffer_pct=claim), RUN, "nothing"))
    assert "Zitat nicht im Text gefunden" in findings[0].message


def test_methodology_quote_needs_three_words() -> None:
    claim = ClaimedValue[str](value="VM0042", quote="VM0042")
    findings = present(compare(ClaimedValues(methodology=claim), RUN, "uses VM0042 here"))
    assert [f.severity for f in findings] == [Severity.INFO]
    assert "Zitat zu kurz als Beleg" in findings[0].message


# --- number format of the text (audit F-20) ---


@pytest.mark.parametrize(
    ("text", "fmt"),
    [
        ("The area covers 100,0 ha and 8.364 tCO2e.", "de"),
        ("The area covers 100.0 ha and 8,364 tCO2e.", "en"),
        ("Removals of 8.364 tCO2e.", None),  # ambiguous only
        ("Signed on 31.10.2026, removals of 8.364 tCO2e.", None),  # a date is no signal
        ("Areas of 100,0 ha and 12.5 ha.", None),  # contradicting signals
    ],
)
def test_number_format_of_text(text: str, fmt: str | None) -> None:
    assert number_format(text) == fmt


def test_misread_number_in_german_text_is_not_backed() -> None:
    # First eval run, case clean-03: the model read "8.364" as 8.364 in a German formatted text.
    text = "The project area covers 100,0 ha. The gross removals amount to 8.364 tCO2e."
    claimed = only("tco2e_gross", 8.364, "The gross removals amount to 8.364 tCO2e.")
    [finding] = present(compare(claimed, RUN, text))
    assert finding.severity is Severity.INFO
    assert "Wert nicht im Zitat belegt" in finding.message


def test_number_read_in_the_text_format_is_backed() -> None:
    text = "The project area covers 100,0 ha. The gross removals amount to 1.000 tCO2e."
    claimed = only("tco2e_gross", 1000.0, "The gross removals amount to 1.000 tCO2e.")
    assert present(compare(claimed, RUN, text)) == []
