"""The eval cases must yield exactly their `expected` findings under a perfect extraction.

Otherwise the evals would measure mistakes in the cases instead of mistakes of the extractor.
A deterministic extractor takes value and quote (a whole sentence or bullet) straight from the text.
"""

import re

import pytest

from carbon_preaudit.domain.models import ClaimedValue, ClaimedValues
from carbon_preaudit.preaudit.compare import compare
from carbon_preaudit.preaudit.extractor import FakeExtractor
from evals.cases import Case, load_cases
from evals.runner import calculate_examples

CASES = load_cases()
RUN = calculate_examples()

SENTENCE_BOUNDARY = re.compile(r"\n|(?<=\.)\s+(?=[A-Z])")
AREA = re.compile(r"project area covers ([\d.,]+) ha")
GROSS = re.compile(r"gross removals of the project amount to ([\d.,]+) tC(?:O2e)?\b")
NET = re.compile(r"net removals[^.]*? amount to ([\d.,]+) tCO2e")
BUFFER = re.compile(r"buffer of ([\d.,]+) %")
METHODOLOGY = re.compile(r"VM\d{4}")


def _number(raw: str) -> float:
    """Parse '8,364' and '8.364' (thousands) as well as '100,0' and '112.5' (decimals)."""
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", raw):
        return float(re.sub(r"[.,]", "", raw))
    return float(raw.replace(",", "."))


def _sentence(text: str, match: re.Match[str]) -> str:
    start = 0
    for boundary in SENTENCE_BOUNDARY.finditer(text):
        if boundary.end() > match.start():
            break
        start = boundary.end()
    nxt = SENTENCE_BOUNDARY.search(text, match.end())
    sentence = text[start : nxt.start() if nxt else len(text)].strip()
    return sentence.removeprefix("- ")


def _number_claim(text: str, pattern: re.Pattern[str]) -> ClaimedValue[float]:
    match = pattern.search(text)
    if match is None:
        return ClaimedValue[float]()
    return ClaimedValue[float](value=_number(match.group(1)), quote=_sentence(text, match))


def perfect_extraction(text: str) -> ClaimedValues:
    """What a flawless extractor returns for `text`: no conversion, verbatim quotes."""
    methodology = METHODOLOGY.search(text)
    return ClaimedValues(
        project_area_ha=_number_claim(text, AREA),
        tco2e_gross=_number_claim(text, GROSS),
        tco2e_net=_number_claim(text, NET),
        buffer_pct=_number_claim(text, BUFFER),
        methodology=(
            ClaimedValue[str]()
            if methodology is None
            else ClaimedValue[str](value=methodology.group(0), quote=_sentence(text, methodology))
        ),
    )


def test_all_twelve_cases_are_loaded() -> None:
    assert len(CASES) == 12


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_perfect_extraction_yields_exactly_the_expected_findings(case: Case) -> None:
    claimed = FakeExtractor(perfect_extraction(case.text)).extract(case.text)
    findings = compare(claimed, RUN, case.text)
    actual = sorted((f.field, f.severity.value, str(f.diagnosis)) for f in findings)
    wanted = sorted((e.field, e.severity.value, str(e.diagnosis)) for e in case.expected)
    assert actual == wanted
