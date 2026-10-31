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

## Im Container starten

Die Befehle gelten für Podman. Mit Docker heißen sie gleich, statt `podman` steht dann `docker`.

Image bauen:

```bash
podman build -t carbon-preaudit .
```

Container im Hintergrund starten. Der Port ist nur auf diesem Rechner erreichbar: Jede Prüfung ruft das LLM
mit deinem Key auf, und es gibt weder Login noch Begrenzung.

```bash
podman run -d --rm -p 127.0.0.1:8000:8000 --name carbon-preaudit carbon-preaudit
```

Health-Check, die Antwort ist `{"status":"ok"}`:

```bash
curl -s localhost:8000/health
```

Die API-Doku liegt unter http://localhost:8000/docs.

Logs ansehen:

```bash
podman logs -f carbon-preaudit
```

Container stoppen. Wegen `--rm` wird er dabei auch entfernt:

```bash
podman stop carbon-preaudit
```

## Versionierung

Die Version setzt nur das Bump-Skript, ausgehend vom letzten Git-Tag. Statt `minor` geht auch `patch`
(Default), `major` oder das Flag `-d` für eine Dev-Version:

```bash
uv run bump version minor
```

Ablauf und Regeln: [ADR 0006](docs/adr/0006-versioning-via-git-tags.md).

## API-Key

Die Extraktion und die Evals rufen ein LLM auf und brauchen einen Schlüssel. Tests und Berechnung laufen ohne ihn.
Für Gemini (Default) genügt ein Key aus Google AI Studio in `GEMINI_API_KEY`. Für Anthropic setzt man
`CARBON_PREAUDIT_PROVIDER=anthropic` und `ANTHROPIC_API_KEY` (ADR 0008). Ist zusätzlich `GOOGLE_API_KEY`
gesetzt (etwa in der Shell), hat dieser Vorrang vor `GEMINI_API_KEY`.

Vorlage kopieren und danach den Schlüssel in `.env` eintragen:

```bash
cp .env.example .env
```

`.env` ist in `.gitignore` eingetragen. uv liest die Datei mit `uv run --env-file .env …`.

## IDE

Als Interpreter `.venv/bin/python` wählen und als Test-Runner pytest.

## Bewusst nicht enthalten

- Methodologiekonforme Berechnung nach VM0047, Unsicherheitsabzüge, Leakage
- PDD-Generierung, RAG über Methodologien, Satellitendaten
- Mandanten, Login, Zugriffsschutz; Postgres/PostGIS (ADR 0003)
- Speicherung der Läufe und Befunde (Schritt 04 zurückgestellt)
- Prüfung, ob die Plots im Polygon liegen oder sich überlappen: Die CSV hat keine Koordinaten.
- Plots ohne Bäume: Das CSV-Format kennt keine Zeile ohne Baum.
- Schnitte zwischen verschiedenen Ringen eines Polygons; geprüft wird nur jeder Ring für sich.
