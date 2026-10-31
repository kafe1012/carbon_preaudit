# Baseline

Stand: Branch `audit/llm-patterns`, abgezweigt von `master` bei `2b61939`, 2026-10-31.

## Rahmen

| Punkt | Wert | Quelle |
|---|---|---|
| Sprache | Python 3.15.2 | `.python-version`, `uv run python --version` |
| Paketmanager | uv 0.13.6, Workspace mit `tools/` | `pyproject.toml`, `uv --version` |
| Laufzeit-Abhängigkeiten | anthropic, fastapi, google-genai, jinja2, pydantic, pyproj, python-multipart, sqlalchemy, uvicorn | `pyproject.toml` |
| Tests | `uv run pytest` | CLAUDE.md |
| Lint / Format | `uv run ruff check .`, `uv run ruff format --check .` | CLAUDE.md |
| Typecheck | `uv run pyright` (strict für `src`, `tools`, `evals`) | `pyproject.toml` |
| Umfang | 6 335 Zeilen ohne `uv.lock`, Eval-Fälle, `docs/`, `.claude/` | `git ls-files` |

## Ergebnis

| Prüfung | Ergebnis |
|---|---|
| `uv run pytest -q -W default` | 332 passed, keine Warnungen |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 74 files already formatted |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations |

Alle Prüfungen waren vor dem Audit grün.

## Analyse-Tools

| Tool | Vorhanden | Verwendet |
|---|---|---|
| vulture (Dead Code) | ja, `/opt/homebrew/bin/vulture` | ja, `--min-confidence 60` |
| gitleaks, trufflehog, detect-secrets | nein | nein, ersetzt durch manuelles `git grep` auf Schlüsselmuster in Dateien und Historie |
| pip-audit, osv-scanner | nein | nein |
| jscpd (Duplikate) | nein | nein |
| semgrep, bandit | nein | nein |

Nicht vorhandene Tools wurden nicht installiert.
