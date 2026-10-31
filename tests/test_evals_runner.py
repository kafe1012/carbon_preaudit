import hashlib
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from google import genai

from carbon_preaudit.calc.params import PARAMS_VERSION
from carbon_preaudit.calc.version import CALC_VERSION
from carbon_preaudit.domain.models import ClaimedValue, ClaimedValues, Severity
from carbon_preaudit.preaudit.extractor import (
    SYSTEM_PROMPT,
    ExtractionError,
    Extractor,
    FakeExtractor,
    GeminiExtractor,
)
from evals.cases import Case, ExpectedFinding
from evals.report import DASH, render_report
from evals.runner import (
    calculate_examples,
    git_revision,
    main,
    prompt_hash,
    requested_model,
    run_cases,
)

TEXT = "The project area covers 500.0 ha of degraded pasture."
CLAIMED = ClaimedValues(
    project_area_ha=ClaimedValue[float](value=500.0, quote="The project area covers 500.0 ha"),
    extracted_by="fake-model-1",
)
CASE_OK = Case(
    id="ok",
    description="d",
    text=TEXT,
    expected=(
        ExpectedFinding(field="project_area_ha", severity=Severity.MAJOR),
        # Everything else is missing from the text: one info finding each.
        ExpectedFinding(field="tco2e_gross", severity=Severity.INFO),
        ExpectedFinding(field="tco2e_net", severity=Severity.INFO),
        ExpectedFinding(field="buffer_pct", severity=Severity.INFO),
        ExpectedFinding(field="methodology", severity=Severity.INFO),
    ),
)
CASE_ERR = Case(id="boom", description="d", text="broken", expected=())


class SelectiveExtractor:
    """Fails for the text of CASE_ERR, answers with CLAIMED otherwise."""

    def extract(self, text: str) -> ClaimedValues:
        if text == CASE_ERR.text:
            raise ExtractionError("model overloaded")
        return FakeExtractor(CLAIMED).extract(text)


def test_runner_counts_extraction_error_as_error() -> None:
    results = run_cases([CASE_OK, CASE_ERR], SelectiveExtractor(), calculate_examples())
    assert results[0].error is None
    assert results[0].score is not None
    assert results[0].score.passed
    assert results[1].findings is None
    assert results[1].score is None
    assert results[1].error == "model overloaded"


def test_report_contains_header_and_tables() -> None:
    run = calculate_examples()
    results = run_cases([CASE_OK, CASE_ERR], SelectiveExtractor(), run)
    report = render_report(
        results,
        run,
        generated_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        app_version="9.9.9",
        provider="gemini",
        model="requested-model-7",
        git_commit="abc1234-dirty",
        prompt_hash="0123456789ab",
    )
    for expected in (
        "2026-01-02 03:04:05",
        "Anbieter: gemini",
        "Modell (angefragt): requested-model-7",
        "Modell (geantwortet): fake-model-1",
        "Git-Commit: abc1234-dirty",
        "Prompt-Hash (SHA-256, 12 Zeichen): 0123456789ab",
        "Bewertet: 1 von 2 Fällen.",
        "1 Fälle mit Extraktionsfehler sind nicht in den Metriken enthalten",
        run.run_hash,
        f"PARAMS_VERSION: {PARAMS_VERSION}",
        f"CALC_VERSION: {CALC_VERSION}",
        "App-Version: 9.9.9",
        "Fälle: 2",
        "Fehler (Extraktion fehlgeschlagen): 1",
        "| project_area_ha | 1 | 0 | 0 | 100 % | 100 % |",
        "| methodology | 1 | 0 | 0 | 100 % | 100 % |",
        "## Diagnosen",
        f"| project_area_ha/major/{DASH}<br>tco2e_gross/info/{DASH}",
        "| ✓ |",
        "model overloaded",
    ):
        assert expected in report


def test_main_writes_report(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    (cases_dir / "a.yaml").write_text(
        "id: a\ndescription: d\ntext: hello world text\nexpected: []\n", encoding="utf-8"
    )
    out = tmp_path / "out" / "latest.md"
    extractor: Extractor = FakeExtractor(ClaimedValues())
    code = main(["--cases", str(cases_dir), "--out", str(out)], lambda: extractor)
    assert code == 0
    assert "# Eval-Bericht" in out.read_text(encoding="utf-8")


def test_main_unknown_only_id_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    (cases_dir / "a.yaml").write_text(
        "id: a\ndescription: d\ntext: x\nexpected: []\n", encoding="utf-8"
    )
    code = main(
        ["--cases", str(cases_dir), "--out", str(tmp_path / "o.md"), "--only", "zzz"],
        lambda: FakeExtractor(ClaimedValues()),
    )
    assert code == 2
    assert "zzz" in capsys.readouterr().err


class FailingExtractor:
    def extract(self, text: str) -> ClaimedValues:
        raise ExtractionError("down")


def test_main_exit_code_is_1_when_an_extraction_failed(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    (cases_dir / "a.yaml").write_text(
        "id: a\ndescription: d\ntext: hello world text\nexpected: []\n", encoding="utf-8"
    )
    out = tmp_path / "o.md"
    code = main(["--cases", str(cases_dir), "--out", str(out)], lambda: FailingExtractor())
    assert code == 1
    assert "Bewertet: 0 von 1 Fällen." in out.read_text(encoding="utf-8")


def test_all_scored_report_says_no_extraction_error() -> None:
    run = calculate_examples()
    report = render_report(
        run_cases([CASE_OK], SelectiveExtractor(), run),
        run,
        generated_at=datetime(2026, 1, 2, tzinfo=UTC),
        app_version="1",
        provider="gemini",
        model="m",
        git_commit=DASH,
        prompt_hash="x",
    )
    assert "Bewertet: 1 von 1 Fällen. Kein Fall mit Extraktionsfehler." in report


def test_prompt_hash_is_first_12_chars_of_sha256() -> None:
    expected = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:12]
    assert prompt_hash() == expected
    assert len(prompt_hash()) == 12


def test_git_revision_clean_dirty_and_without_git(tmp_path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

    assert git_revision(tmp_path) == DASH  # not a repository
    git("init", "-q")
    (tmp_path / "f.txt").write_text("a", encoding="utf-8")
    git("add", ".")
    git("commit", "-q", "-m", "init", "--no-gpg-sign")
    clean = git_revision(tmp_path)
    assert clean != DASH
    assert not clean.endswith("-dirty")
    (tmp_path / "evals" / "results").mkdir(parents=True)
    (tmp_path / "evals" / "results" / "latest.md").write_text("r", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "x.md").write_text("x", encoding="utf-8")
    assert git_revision(tmp_path) == clean  # report and agent config are ignored
    (tmp_path / "f.txt").write_text("b", encoding="utf-8")
    assert git_revision(tmp_path) == f"{clean}-dirty"


def test_requested_model_comes_from_the_extractor() -> None:
    gemini = GeminiExtractor(client=cast(genai.Client, object()), model="custom-1")
    assert requested_model(gemini) == "custom-1"
    assert requested_model(FakeExtractor(ClaimedValues())) == DASH
