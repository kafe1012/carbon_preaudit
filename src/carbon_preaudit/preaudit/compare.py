"""Deterministic comparison of claimed values with a calculation run. Pure, no I/O."""

import math
import re
from typing import Literal

from carbon_preaudit.calc.params import (
    CO2_PER_C,
    EXPECTED_METHODOLOGY,
    TOL_AREA_REL,
    TOL_BUFFER_ABS,
    TOL_TONNES_REL,
)
from carbon_preaudit.domain.models import (
    CalculationRun,
    ClaimedValue,
    ClaimedValues,
    Diagnosis,
    Finding,
    FindingField,
    Severity,
)

FIELD_ORDER: tuple[FindingField, ...] = (
    "project_area_ha",
    "tco2e_gross",
    "tco2e_net",
    "buffer_pct",
    "methodology",
)
_SEVERITY_ORDER = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.INFO: 2}
LABELS: dict[FindingField, str] = {
    "project_area_ha": "Projektfläche",
    "tco2e_gross": "Brutto-Menge (tCO₂e)",
    "tco2e_net": "Netto-Menge (tCO₂e)",
    "buffer_pct": "Pufferanteil",
    "methodology": "Methodologie",
}
# Float equality between an extracted value and a number read from the quote; technical, not
# a domain value, hence not in params.py.
_QUOTE_VALUE_REL_TOL = 1e-9
MIN_QUOTE_WORDS = 3
_CHUNK = re.compile(r"\d+(?:[.,']\d+)*")
_HEAD_GROUP = re.compile(r"\d{1,3}")
_NEXT_GROUP = re.compile(r"\d{3}(?:[.,']\d+)*")
_GROUP_SEPARATORS = " \u00a0\u202f"  # space, no-break space, narrow no-break space
_WORD_CHAR = re.compile(r"\w")
_LETTER = re.compile(r"[^\W\d_]")
_MINUS_SIGNS = "-\u2212"
_VM_CODE = re.compile(r"VM\d{4}")
_WHITESPACE_OR_HYPHEN = re.compile(r"[\s\-\u2010-\u2015\u2212]+")


def squash(text: str) -> str:
    """Normalize all whitespace runs (including no-break and narrow spaces) to one space."""
    return " ".join(text.split())


def format_de(x: float, digits: int) -> str:
    """Format with German separators: 1.234,5."""
    s = f"{x:,.{digits}f}"
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


type NumberFormat = Literal["de", "en"]

# Numbers only one format writes this way: a decimal part of 1-2 or 4+ digits, or both separators.
# Neighbouring digits/separators are excluded so that dates like "31.10.2026" give no signal.
_DE_SIGNAL = re.compile(
    r"(?<![\d.,])\d+,(?:\d{1,2}|\d{4,})(?![.,]?\d)|(?<![\d.,])\d{1,3}(?:\.\d{3})+,\d"
)
_EN_SIGNAL = re.compile(
    r"(?<![\d.,])\d+\.(?:\d{1,2}|\d{4,})(?![.,]?\d)|(?<![\d.,])\d{1,3}(?:,\d{3})+\.\d"
)


def number_format(text: str) -> NumberFormat | None:
    """The number format of the whole text, or None if it gives no or contradicting signals.

    "100,0 ha" marks German, "100.0 ha" English; "8.364" alone is ambiguous.
    """
    de, en = bool(_DE_SIGNAL.search(text)), bool(_EN_SIGNAL.search(text))
    if de == en:
        return None
    return "de" if de else "en"


def _readings(segment: str, fmt: NumberFormat | None = None) -> set[float]:
    """Numeric readings of a digit group with ., or ' separators.

    With an unknown format an ambiguous group ("8.364") counts under both readings; with a known
    format only under that one.
    """
    s = segment.replace("'", "")
    out: set[float] = set()
    dots, commas = s.count("."), s.count(",")
    if dots and commas:
        decimal = "." if s.rfind(".") > s.rfind(",") else ","
        thousands = "," if decimal == "." else "."
        if s.count(decimal) == 1:
            out.add(float(s.replace(thousands, "").replace(decimal, ".")))
        return out
    sep = "." if dots else "," if commas else ""
    if not sep:
        out.add(float(s))
        return out
    head, *groups = s.split(sep)
    decimal_reading = float(f"{head}.{groups[0]}") if len(groups) == 1 else None
    thousands_reading = (
        float(head + "".join(groups))
        if not head.startswith("0") and all(len(g) == 3 for g in groups)
        else None
    )
    if decimal_reading is not None and thousands_reading is not None and fmt is not None:
        thousands_sep = "." if fmt == "de" else ","
        return {thousands_reading if sep == thousands_sep else decimal_reading}
    return {r for r in (decimal_reading, thousands_reading) if r is not None}


def _number_groups(quote: str) -> list[tuple[int, int, str]]:
    """Digit sequences of the quote as (start, end, text), thousands groups merged greedily.

    A group of 1-3 digits followed by single-space-separated groups of exactly 3 digits is one
    number ("20 100" is 20100, not 20 and 100); the groups of a valid number are no candidates
    on their own. Line breaks never separate thousands.
    """
    chunks = [(m.start(), m.end(), m.group()) for m in _CHUNK.finditer(quote)]
    out: list[tuple[int, int, str]] = []
    i = 0
    while i < len(chunks):
        start, end, text = chunks[i]
        j = i + 1
        if _HEAD_GROUP.fullmatch(text):
            while (
                j < len(chunks)
                and chunks[j][0] == end + 1
                and quote[end] in _GROUP_SEPARATORS
                and _NEXT_GROUP.fullmatch(chunks[j][2])
            ):
                text += chunks[j][2]
                end = chunks[j][1]
                j += 1
                if re.search(r"[.,']", chunks[j - 1][2]):
                    break  # a decimal part ends the number
        out.append((start, end, text))
        i = j
    return out


def number_candidates(quote: str, fmt: NumberFormat | None = None) -> set[float]:
    """All numbers in the quote; ambiguous ones count under both readings unless `fmt` is known.

    Behaviour worth knowing:
    - A sign directly before a number is kept ("-5 %" is -5), unless the sign follows a letter
      or digit ("8,000-9,000").
    - Ranges give both ends as candidates ("8,000-9,000" is 8000 and 9000).
    - Digits that touch a letter are no numbers ("tCO2e", "VM0047"), so scientific notation
      ("1.2e4") yields no candidate at all: the value counts as not backed, the safe direction.
    """
    out: set[float] = set()
    for start, end, text in _number_groups(quote):
        if start > 0 and _LETTER.match(quote[start - 1]):
            continue
        if end < len(quote) and _LETTER.match(quote[end]):
            continue
        readings = _readings(text, fmt)
        negative = (
            start > 0
            and quote[start - 1] in _MINUS_SIGNS
            and (start == 1 or not quote[start - 2].isalnum())
        )
        out |= {-r for r in readings} if negative else readings
    return out


def _value_in_quote(value: float, quote: str, fmt: NumberFormat | None) -> bool:
    return any(
        math.isclose(value, c, rel_tol=_QUOTE_VALUE_REL_TOL) for c in number_candidates(quote, fmt)
    )


def quote_in_text(quote: str, text: str) -> bool:
    """The quote occurs verbatim (whitespace normalized) in the text."""
    return squash(quote) in squash(text)


def squash_with_offsets(text: str) -> tuple[str, list[int]]:
    """Squashed text (same rule as `squash`) and, per squashed char, the original index.

    The separator space between two words maps to -1.
    """
    parts: list[str] = []
    offsets: list[int] = []
    for i, m in enumerate(re.finditer(r"\S+", text)):
        if i > 0:
            parts.append(" ")
            offsets.append(-1)
        parts.append(m.group())
        offsets.extend(range(m.start(), m.end()))
    return "".join(parts), offsets


def evidence_span(quote: str, text: str) -> tuple[int, int] | None:
    """Span (start, end) in the original text where the quote counts as evidence, or None.

    At least MIN_QUOTE_WORDS words, and the quote starts and ends on word boundaries.
    A digit is not on a boundary when it continues a longer number: "0 ha" is no evidence
    in "100.0 ha". The first match on a boundary counts.
    """
    q = squash(quote)
    if len(q.split()) < MIN_QUOTE_WORDS:
        return None
    before = r"(?<![\w])(?<!\d[.,'])" if _WORD_CHAR.match(q[0]) else ""
    after = r"(?![\w])(?![.,']\d)" if _WORD_CHAR.match(q[-1]) else ""
    squashed, offsets = squash_with_offsets(text)
    match = re.search(before + re.escape(q) + after, squashed)
    if match is None:
        return None
    return offsets[match.start()], offsets[match.end() - 1] + 1


def _quote_is_evidence(quote: str, text: str) -> bool:
    return evidence_span(quote, text) is not None


def _normalize_methodology(text: str) -> str:
    return _WHITESPACE_OR_HYPHEN.sub("", text).upper()


def _within_rel(c: float, k: float, tol: float) -> bool:
    if k == 0:
        return c == 0
    return abs(c - k) / k <= tol


def _rel(c: float, k: float) -> float | None:
    return None if k == 0 else (c - k) / k


def _info(
    field: FindingField,
    claimed: float | str | None,
    computed: float | str,
    quote: str | None,
    msg: str,
) -> Finding:
    return Finding(
        field=field,
        severity=Severity.INFO,
        claimed=claimed,
        computed=computed,
        quote=quote,
        message=msg,
    )


def _check_number(
    field: FindingField, c: float, quote: str, k: float, run: CalculationRun
) -> Finding | None:
    label = LABELS[field]
    if field == "project_area_ha":
        if _within_rel(c, k, TOL_AREA_REL):
            return None
        severity, digits, unit = Severity.MAJOR, 2, "ha"
    elif field == "buffer_pct":
        if math.isclose(c, k, abs_tol=TOL_BUFFER_ABS):
            return None
        severity, digits, unit = Severity.MAJOR, 2, "%"
    else:
        if _within_rel(c, k, TOL_TONNES_REL):
            return None
        severity, digits, unit = Severity.CRITICAL, 1, "tCO₂e"
    diagnosis = _diagnose(field, c, k, run)
    claimed_unit = "tC" if diagnosis is Diagnosis.TC_INSTEAD_OF_TCO2E else unit
    message = (
        f"{label}: behauptet {format_de(c, digits)} {claimed_unit}, "
        f"berechnet {format_de(k, digits)} {unit}"
    )
    rel = _rel(c, k)
    if rel is not None:
        message += f" (Abweichung {'+' if rel >= 0 else '-'}{format_de(abs(rel) * 100, 1)} %)"
    message += "."
    if diagnosis is Diagnosis.TC_INSTEAD_OF_TCO2E:
        message += " Vermutlich tC statt tCO₂e."
    elif diagnosis is Diagnosis.GROSS_NET_SWAPPED:
        message += " Brutto/netto verwechselt."
    return Finding(
        field=field,
        severity=severity,
        claimed=c,
        computed=k,
        quote=quote,
        deviation_rel=rel,
        diagnosis=diagnosis,
        message=message,
    )


def _diagnose(field: FindingField, c: float, k: float, run: CalculationRun) -> Diagnosis | None:
    if field not in ("tco2e_gross", "tco2e_net"):
        return None
    if _within_rel(c, k / CO2_PER_C, TOL_TONNES_REL):
        return Diagnosis.TC_INSTEAD_OF_TCO2E
    if field == "tco2e_net" and _within_rel(c, run.tco2e_gross, TOL_TONNES_REL):
        return Diagnosis.GROSS_NET_SWAPPED
    return None


def _check_methodology(value: str, quote: str) -> Finding | None:
    match = _VM_CODE.search(_normalize_methodology(value))
    if match is not None and match.group() == EXPECTED_METHODOLOGY:
        return None
    if match is None:
        msg = (
            f"Methodologie: behauptet „{value}“ enthält keinen VM-Code, "
            f"erwartet {EXPECTED_METHODOLOGY}."
        )
    else:
        msg = f"Methodologie: behauptet {match.group()}, erwartet {EXPECTED_METHODOLOGY}."
    return Finding(
        field="methodology",
        severity=Severity.MAJOR,
        claimed=value,
        computed=EXPECTED_METHODOLOGY,
        quote=quote,
        message=msg,
    )


def _check_numeric_field(
    field: FindingField, claim: ClaimedValue[float], k: float, run: CalculationRun, text: str
) -> Finding | None:
    label = LABELS[field]
    value, quote = claim.value, claim.quote
    if value is None or quote is None:
        return _info(field, None, k, None, f"{label}: im Text nicht gefunden.")
    if not quote_in_text(quote, text):
        return _info(field, value, k, quote, f"{label}: Zitat nicht im Text gefunden.")
    if not _quote_is_evidence(quote, text):
        return _info(field, value, k, quote, f"{label}: Zitat zu kurz als Beleg.")
    if not _value_in_quote(value, quote, number_format(text)):
        return _info(field, value, k, quote, f"{label}: Wert nicht im Zitat belegt.")
    return _check_number(field, value, quote, k, run)


def _check_methodology_field(claim: ClaimedValue[str], text: str) -> Finding | None:
    label = LABELS["methodology"]
    value, quote = claim.value, claim.quote
    expected = EXPECTED_METHODOLOGY
    if value is None or quote is None:
        return _info("methodology", None, expected, None, f"{label}: im Text nicht gefunden.")
    if not quote_in_text(quote, text):
        return _info(
            "methodology", value, expected, quote, f"{label}: Zitat nicht im Text gefunden."
        )
    if not _quote_is_evidence(quote, text):
        return _info("methodology", value, expected, quote, f"{label}: Zitat zu kurz als Beleg.")
    if _normalize_methodology(value) not in _normalize_methodology(quote):
        return _info("methodology", value, expected, quote, f"{label}: Wert nicht im Zitat belegt.")
    return _check_methodology(value, quote)


def compare(claimed: ClaimedValues, run: CalculationRun, text: str) -> list[Finding]:
    """Compare claimed values with the run. Order: field order, then severity."""
    results = (
        _check_numeric_field(
            "project_area_ha", claimed.project_area_ha, run.project_area_ha, run, text
        ),
        _check_numeric_field("tco2e_gross", claimed.tco2e_gross, run.tco2e_gross, run, text),
        _check_numeric_field("tco2e_net", claimed.tco2e_net, run.tco2e_net, run, text),
        _check_numeric_field("buffer_pct", claimed.buffer_pct, run.buffer_pct, run, text),
        _check_methodology_field(claimed.methodology, text),
    )
    findings = [f for f in results if f is not None]
    findings.sort(key=lambda f: (FIELD_ORDER.index(f.field), _SEVERITY_ORDER[f.severity]))
    return findings
