"""Runs the cases through an extractor and the deterministic comparison."""

import argparse
import hashlib
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from carbon_preaudit.calc.inputs import InputError, parse_inputs
from carbon_preaudit.calc.run import calculate
from carbon_preaudit.domain.models import CalculationRun, Finding
from carbon_preaudit.preaudit.compare import compare
from carbon_preaudit.preaudit.extractor import (
    DEFAULT_PROVIDER,
    PROVIDER_ENV_VAR,
    SYSTEM_PROMPT,
    AnthropicExtractor,
    ExtractionError,
    Extractor,
    GeminiExtractor,
    make_extractor,
)

from .cases import DEFAULT_CASES_DIR, Case, CaseError, load_cases
from .report import DASH, render_report
from .scorer import CaseScore, match_case

REPO_ROOT = Path(__file__).parent.parent
EXAMPLES = REPO_ROOT / "examples"
DEFAULT_OUT = Path(__file__).parent / "results" / "latest.md"


@dataclass(frozen=True)
class CaseResult:
    """Outcome of one case: findings, or an error message if extraction failed."""

    case: Case
    findings: tuple[Finding, ...] | None
    extracted_by: str | None = None
    error: str | None = None

    @property
    def score(self) -> CaseScore | None:
        if self.findings is None:
            return None
        return match_case(self.case.expected, self.findings)


def calculate_examples() -> CalculationRun:
    """The one calculation run all cases are compared against."""
    return calculate(
        parse_inputs(
            (EXAMPLES / "project.geojson").read_text(encoding="utf-8"),
            (EXAMPLES / "plots.csv").read_text(encoding="utf-8"),
        )
    )


DIRTY_EXCLUDES = ("evals/results", ".claude")


def git_revision(cwd: Path = REPO_ROOT) -> str:
    """Short commit, suffixed with '-dirty' for uncommitted changes. En dash without git.

    The report itself (`evals/results/`) and local agent config (`.claude/`) do not count as
    changes: neither affects a run, and the report would otherwise mark every re-run as dirty.
    """
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", ".", *(f":!{p}" for p in DIRTY_EXCLUDES)],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except OSError, subprocess.CalledProcessError:
        return DASH
    if not commit:
        return DASH
    return f"{commit}-dirty" if status else commit


def prompt_hash() -> str:
    """First 12 hex characters of the SHA-256 of SYSTEM_PROMPT."""
    return hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:12]


def requested_model(extractor: Extractor) -> str:
    """The model the extractor asks for, as the extractor itself reports it."""
    if isinstance(extractor, AnthropicExtractor | GeminiExtractor):
        return extractor.model
    return DASH


def run_cases(cases: Sequence[Case], extractor: Extractor, run: CalculationRun) -> list[CaseResult]:
    """Extract and compare each case. An ExtractionError only fails that case."""
    results: list[CaseResult] = []
    for case in cases:
        try:
            claimed = extractor.extract(case.text)
        except ExtractionError as e:
            results.append(CaseResult(case, None, error=str(e)))
            continue
        findings = compare(claimed, run, case.text)
        results.append(CaseResult(case, tuple(findings), extracted_by=claimed.extracted_by))
    return results


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m evals", description="Run the eval cases.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_DIR, help="case directory")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="report file")
    parser.add_argument("--only", action="append", default=[], metavar="ID", help="case id")
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    extractor_factory: Callable[[], Extractor] = make_extractor,
) -> int:
    """CLI entry point. Returns the exit code."""
    args = _parse_args(argv)
    cases_dir: Path = args.cases
    out: Path = args.out
    only: list[str] = args.only
    try:
        cases = load_cases(cases_dir)
        if only:
            unknown = sorted(set(only) - {c.id for c in cases})
            if unknown:
                raise CaseError(f"unknown case ids: {', '.join(unknown)}")
            cases = [c for c in cases if c.id in only]
        if not cases:
            raise CaseError(f"{cases_dir}: no cases found")
        run = calculate_examples()
        extractor = extractor_factory()
    except (CaseError, InputError, ExtractionError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    results = run_cases(cases, extractor, run)
    provider = os.environ.get(PROVIDER_ENV_VAR) or DEFAULT_PROVIDER
    report = render_report(
        results,
        run,
        generated_at=datetime.now(UTC),
        app_version=version("carbon-preaudit"),
        provider=provider,
        model=requested_model(extractor),
        git_commit=git_revision(),
        prompt_hash=prompt_hash(),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    failed = sum(1 for r in results if r.error is not None)
    print(f"{len(results)} cases, {failed} errors, report: {out}")
    # Exit 1 if any extraction failed; low metrics alone never fail the run.
    return 1 if failed else 0
