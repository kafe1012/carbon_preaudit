# carbon-preaudit

Pre-Audit-Check für naturbasierte CO₂-Projekte. Worum es geht, steht in
[docs/problem-statement.md](docs/problem-statement.md).

## Voraussetzungen

- Git
- [uv](https://docs.astral.sh/uv/getting-started/installation/) ≥ 0.13. uv installiert Python 3.15
  selbst, die Version steht in `.python-version`.
- Optional Node.js für den commitlint-Hook. Fehlt Node, lädt pre-commit eine eigene Version.

## Einrichten

Repo klonen:

```bash
git clone https://github.com/kafe1012/carbon_preaudit.git
```

In den Ordner wechseln:

```bash
cd carbon_preaudit
```

`.venv/` anlegen und alle Abhängigkeiten aus `uv.lock` installieren:

```bash
uv sync
```

Git-Hooks einrichten. Danach laufen vor jedem Commit ruff, pyright und `uv lock`, und commitlint prüft
die Commit-Nachricht auf Conventional Commits:

```bash
uv run pre-commit install
```

## Prüfen

Alle Hooks auf allen Dateien:

```bash
uv run pre-commit run --all-files
```

Tests:

```bash
uv run pytest
```

## Versionierung

Die Version setzt nur das Bump-Skript, ausgehend vom letzten Git-Tag. Statt `minor` geht auch `patch`
(Default), `major` oder das Flag `-d` für eine Dev-Version:

```bash
uv run bump version minor
```

Ablauf und Regeln: [ADR 0006](docs/adr/0006-versioning-via-git-tags.md).

## API-Key

Die Evals rufen die Anthropic API auf und brauchen einen Schlüssel. Tests und Berechnung laufen ohne ihn.

Vorlage kopieren und danach `ANTHROPIC_API_KEY` in `.env` eintragen:

```bash
cp .env.example .env
```

`.env` ist in `.gitignore` eingetragen. uv liest die Datei mit `uv run --env-file .env …`.

## IDE

Als Interpreter `.venv/bin/python` wählen und als Test-Runner pytest.
