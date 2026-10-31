"""Markdown report (German) of an eval run."""

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from carbon_preaudit.calc.params import PARAMS_VERSION
from carbon_preaudit.calc.version import CALC_VERSION
from carbon_preaudit.domain.models import CalculationRun, Finding

from .cases import ExpectedFinding
from .scorer import FIELDS, Counts, aggregate

if TYPE_CHECKING:
    from .runner import CaseResult

DASH = "\N{EN DASH}"


def _pct(value: float | None) -> str:
    return DASH if value is None else f"{value * 100:.0f} %"


def _label(item: ExpectedFinding | Finding) -> str:
    diagnosis = item.diagnosis.value if item.diagnosis else DASH
    return f"{item.field}/{item.severity.value}/{diagnosis}"


def _list(items: Sequence[ExpectedFinding] | Sequence[Finding]) -> str:
    return "<br>".join(_label(i) for i in items) if items else DASH


def _counts_row(name: str, c: Counts) -> str:
    return f"| {name} | {c.tp} | {c.fp} | {c.fn} | {_pct(c.precision)} | {_pct(c.recall)} |"


def _answered_by(results: Sequence[CaseResult]) -> str:
    models = sorted({r.extracted_by for r in results if r.extracted_by})
    return ", ".join(models) if models else DASH


def _coverage_note(errors: int) -> str:
    if not errors:
        return "Kein Fall mit Extraktionsfehler."
    return (
        f"{errors} Fälle mit Extraktionsfehler sind nicht in den Metriken enthalten, "
        "ihre erwarteten Befunde zählen nicht als FN."
    )


def render_report(
    results: Sequence[CaseResult],
    run: CalculationRun,
    *,
    generated_at: datetime,
    app_version: str,
    provider: str,
    model: str,
    git_commit: str,
    prompt_hash: str,
) -> str:
    """Render the report. Cases with an extraction error are listed but not scored."""
    scored = [(r, s) for r in results if (s := r.score) is not None]
    totals = aggregate([s for _, s in scored])
    errors = [r for r in results if r.error is not None]
    lines = [
        "# Eval-Bericht",
        "",
        f"- Zeitpunkt (UTC): {generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Anbieter: {provider}",
        f"- Modell (angefragt): {model}",
        f"- Modell (geantwortet): {_answered_by(results)}",
        f"- run_hash: `{run.run_hash}`",
        f"- PARAMS_VERSION: {PARAMS_VERSION}",
        f"- CALC_VERSION: {CALC_VERSION}",
        f"- App-Version: {app_version}",
        f"- Git-Commit: {git_commit}",
        f"- Prompt-Hash (SHA-256, 12 Zeichen): {prompt_hash}",
        f"- Fälle: {len(results)}",
        f"- Fehler (Extraktion fehlgeschlagen): {len(errors)}",
        "",
        f"Bewertet: {len(scored)} von {len(results)} Fällen. {_coverage_note(len(errors))}",
        "",
        "## Je Feld",
        "",
        "| Feld | TP | FP | FN | Precision | Recall |",
        "|---|---|---|---|---|---|",
        *(_counts_row(f, totals.per_field[f]) for f in FIELDS),
        _counts_row("**gesamt**", totals.overall),
        "",
        "## Diagnosen",
        "",
        "| Erwartet | Richtig | Unerwartet |",
        "|---|---|---|",
        f"| {totals.diagnoses.expected} | {totals.diagnoses.correct} | "
        f"{totals.diagnoses.unexpected} |",
        "",
        "## Je Fall",
        "",
        "Format: field/severity/diagnosis",
        "",
        "| Fall | Erwartet | Tatsächlich | Ergebnis |",
        "|---|---|---|---|",
    ]
    for r in results:
        if r.findings is None:
            lines.append(f"| {r.case.id} | {_list(r.case.expected)} | Fehler | ✗ |")
            continue
        score = r.score
        mark = "✓" if score is not None and score.passed else "✗"
        lines.append(f"| {r.case.id} | {_list(r.case.expected)} | {_list(r.findings)} | {mark} |")
    failed = [(r, s) for r, s in scored if not s.passed]
    if failed or errors:
        lines += ["", "## Fehlschläge", ""]
        for r in errors:
            lines.append(f"- **{r.case.id}**: Extraktion fehlgeschlagen: {r.error}")
        for r, s in failed:
            for exp in s.misses:
                lines.append(f"- **{r.case.id}**: fehlt: {_label(exp)}")
            for f in s.extras:
                lines.append(f"- **{r.case.id}**: unerwartet: {_label(f)}: {f.message}")
    return "\n".join(lines) + "\n"
