"""Mark verified quotes in the PDD text. Pure, no I/O.

The text is HTML-escaped piece by piece; markup is only added around escaped pieces.
"""

import html
from collections.abc import Sequence
from dataclasses import dataclass

from markupsafe import Markup

from carbon_preaudit.domain.models import ClaimedValue, ClaimedValues, Finding
from carbon_preaudit.preaudit.compare import (
    FIELD_ORDER,
    LABELS,
    evidence_span,
    quote_in_text,
    squash,
    squash_with_offsets,
)

OK_LEVEL = "ok"
# Highest priority first; on overlapping quotes the more severe one wins.
LEVEL_ORDER = ("critical", "major", "info", OK_LEVEL)


@dataclass(frozen=True)
class Mark:
    """A quote to mark in the text. `level` is a Severity value or OK_LEVEL."""

    quote: str
    level: str
    label: str


def build_marks(claimed: ClaimedValues, findings: Sequence[Finding]) -> list[Mark]:
    """One mark per quote that occurs in the text; level from the finding of its field."""
    levels = {f.field: f.severity.value for f in findings}
    marks: list[Mark] = []
    for field in FIELD_ORDER:
        claim: ClaimedValue[float] | ClaimedValue[str] = getattr(claimed, field)
        quote = claim.quote
        if quote is not None:
            marks.append(Mark(quote, levels.get(field, OK_LEVEL), LABELS[field]))
    return marks


def _span(quote: str, text: str, squashed: str, offsets: list[int]) -> tuple[int, int] | None:
    """The span compare counts as evidence; for quotes that are no evidence the first occurrence."""
    span = evidence_span(quote, text)
    if span is not None:
        return span
    q = squash(quote)
    if not q or not quote_in_text(quote, text):
        return None
    s = squashed.find(q)
    if s < 0:
        return None
    return offsets[s], offsets[s + len(q) - 1] + 1


def highlight(text: str, marks: Sequence[Mark]) -> Markup:
    """Escape the text and wrap each found quote in a <mark>.

    Evidence quotes are marked where compare counts them. Fields that share a quote share one
    mark: the more severe level colors it, the title lists all labels.
    """
    squashed, offsets = squash_with_offsets(text)
    placed: list[tuple[int, int, Mark, list[str]]] = []
    for mark in sorted(marks, key=lambda m: LEVEL_ORDER.index(m.level)):
        span = _span(mark.quote, text, squashed, offsets)
        if span is None:
            continue
        start, end = span
        same = [p for p in placed if p[0] == start and p[1] == end]
        if same:
            same[0][3].append(mark.label)
            continue
        if any(start < pe and ps < end for ps, pe, _, _ in placed):
            continue
        placed.append((start, end, mark, [mark.label]))
    placed.sort(key=lambda p: p[0])
    out: list[str] = []
    pos = 0
    for start, end, mark, labels in placed:
        out.append(html.escape(text[pos:start]))
        title = html.escape(", ".join(labels))
        out.append(
            f'<mark class="hl hl-{html.escape(mark.level)}" title="{title}">'
            f"{html.escape(text[start:end])}</mark>"
        )
        pos = end
    out.append(html.escape(text[pos:]))
    # Every piece above is escaped, so the joined string is safe markup.
    return Markup("".join(out))
