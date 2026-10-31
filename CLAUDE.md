# carbon-preaudit

Demo-Projekt: Ein Pre-Audit-Check für naturbasierte CO₂-Projekte (Aufforstung).
Es prüft, ob die Zahlen in einem PDD-Textabschnitt zu den tatsächlichen Projektdaten passen,
bevor ein Auditor die Abweichung findet.

## Leitprinzipien (nicht verhandelbar)

1. **KI liest, Code rechnet.** Das LLM extrahiert nur behauptete Werte aus Text.
   Jede Berechnung und jede Bewertung passiert deterministisch in Python.
2. **Reproduzierbare Läufe.** Gleiche Eingaben + gleiche Parameter-Version + gleiche Code-Version
   = gleiches Ergebnis und gleicher Hash.
3. **Jeder Befund ist belegbar.** Ein Befund nennt: Feld, behaupteter Wert, berechneter Wert,
   Textstelle (wörtliches Zitat), Schweregrad.
4. **Tiefe vor Breite.** Was nicht im Scope steht, wird nicht gebaut, auch nicht „schnell nebenbei“.

## Scope

- Eingabe A: Projektfläche als GeoJSON-Polygon (WGS84)
- Eingabe B: Messdaten als CSV: `plot_id, plot_area_m2, tree_id, dbh_cm, height_m, wood_density`
  (`wood_density` in g/cm³, optional, Default 0.6 aus Parametern; der Lauf zählt,
  für wie viele Bäume der Default verwendet wurde)
- Berechnungslauf:
  - Fläche in ha (geodätisch, `pyproj.Geod`)
  - Oberirdische Biomasse je Baum: Chave et al. 2014, `AGB_kg = 0.0673 * (ρ * D² * H) ** 0.976`
  - Kohlenstoff = Biomasse × 0.47, CO₂e = C × 44/12
  - tCO₂e/ha flächengewichtet: Σ tCO₂e aller Plots / Σ Plot-Fläche in ha, × `project_area_ha`
  - Pufferabzug (`buffer_pct` in Prozent, Default 20), Ergebnis = handelbare tCO₂e
  - Alle Konstanten in `src/carbon_preaudit/calc/params.py` mit `PARAMS_VERSION`
  - Hash über kanonische Eingaben + `PARAMS_VERSION` + `CALC_VERSION` (ADR 0002)
- Pre-Audit:
  - LLM extrahiert `ClaimedValues` (project_area_ha, tco2e_gross, tco2e_net, buffer_pct,
    methodology), jeweils mit wörtlichem Zitat oder `null`, ohne Umrechnung
  - Deterministischer Abgleich, Toleranzen relativ zum berechneten Wert
    (`|c − k| / k`): Fläche 1 %, Tonnen 2 %; Puffer `math.isclose(abs_tol=0.01)`;
    Methodologie per `VM\d{4}` normalisiert, erwartet VM0047
  - Schweregrade: Tonnen abweichend → kritisch; Fläche, Puffer, Methodologie abweichend → wichtig;
    Wert fehlt → hinweis
  - Diagnosen: behauptet ≈ berechnet / (44/12) → „vermutlich tC statt tCO₂e“;
    behauptetes Netto ≈ berechnetes Brutto → „brutto/netto verwechselt“
  - Zitat nicht wörtlich im Text → Wert wird nicht verglichen, Befund „hinweis“
  - Zitat nur Beleg an Wortgrenzen und mit mindestens 3 Wörtern, sonst nicht verglichen, Befund „hinweis“
  - Wert nicht im Zitat (Zahlen normalisiert, deutsch und englisch) → nicht verglichen, Befund „hinweis“
  - Ergebnis: Liste von `Finding`; Details in `docs/plans/01-architecture.md`
- Evals: Testfälle mit absichtlich eingebauten Fehlern, Metriken Precision/Recall
- Eine Weboberfläche: Karte, Kennzahlen, markierter Text, Befundliste

## Bewusst nicht im Scope

Methodologiekonforme Berechnung (VM0047), Unsicherheitsabzüge, Leakage, PDD-Generierung,
RAG über Methodologien, Satellitendaten, Mandanten/Login, Postgres/PostGIS.
Diese Punkte landen nur im README-Abschnitt „Bewusst nicht enthalten“.

## Stack

- Python 3.15, **uv** (kein pip, kein poetry)
- **ruff** (Lint + Format), **pyright** (strict für `src/`), **pytest**
- **pre-commit**: ruff, pyright und `uv lock` vor jedem Commit, commitlint (Conventional Commits)
  auf jede Commit-Nachricht; Hooks nie mit `--no-verify` umgehen
- FastAPI, Pydantic v2, Jinja2 + HTMX, Leaflet (beides per CDN, Version gepinnt)
- SQLAlchemy 2 mit SQLite (ADR begründet den späteren Wechsel zu Postgres)
- Anthropic Python SDK hinter eigener Schnittstelle `Extractor` (Protocol); kein LangChain
- Docker (ein Dockerfile), GitHub Actions
- Versionierung: dunamai (Version aus Git-Tag), git-changelog (Release-Notes), click (Bump-CLI in `tools/`), ADR 0006

## Befehle

Einrichtung eines Rechners: siehe `README.md`.

Alle Hooks auf allen Dateien:

```bash
uv run pre-commit run --all-files
```

Lint:

```bash
uv run ruff check .
```

Formatierung prüfen:

```bash
uv run ruff format --check .
```

Typprüfung:

```bash
uv run pyright
```

Tests:

```bash
uv run pytest
```

Version setzen (`major`, `minor`, `patch` oder `-d`, nur auf Anweisung des Menschen, ADR 0006):

```bash
uv run bump version minor
```

Web-App lokal:

```bash
uv run uvicorn carbon_preaudit.web.app:app --reload
```

Evals (braucht `ANTHROPIC_API_KEY` in `.env`):

```bash
uv run --env-file .env python -m evals
```

## Struktur

```
src/carbon_preaudit/
  domain/      # Pydantic-Modelle: Plot, Tree, CalculationRun, ClaimedValues, Finding
  calc/        # Fläche, Allometrie, Hash, params.py
  preaudit/    # extractor.py (Protocol + Anthropic + Fake), compare.py
  store/       # Persistenz der Läufe
  web/         # FastAPI-App, Templates
evals/         # cases/*.yaml, scorer, results/
examples/      # Beispiel-GeoJSON, -CSV, -PDD-Texte
docs/          # plans/, adr/, reviews/
tools/         # eigenes uv-Paket local_tools: Bump-Skript (`uv run bump`), nie deployt
```

## Code-Konventionen

- Bezeichner, Docstrings und Commits auf Englisch; Doku in `docs/` und README auf Deutsch
- Type Hints überall, keine `Any` in `src/`
- Reine Funktionen in `calc/` und `preaudit/compare.py`, keine I/O dort
- Jede Logikänderung in `calc/` erhöht `CALC_VERSION`, jede Wertänderung in `params.py`
  erhöht `PARAMS_VERSION`; Golden-Tests führen Sollwerte nach Version
- Kein Netzwerkzugriff in Unit-Tests: immer `FakeExtractor`
- Fehler als eigene Exception-Klassen, keine nackten `except`

## Arbeitsweise mit Agenten

1. **Planen:** Hauptsession (Opus) schreibt Plan nach `docs/plans/NN-<thema>.md`. Mensch gibt frei.
2. **Umsetzen:** Subagent `implementer` (Sonnet) setzt genau einen Plan-Schritt um.
3. **Prüfen:** ruff, pyright, pytest müssen grün sein, bevor ein Review startet.
4. **Review:** Subagent `reviewer` (Fable) schreibt Befunde nach `docs/reviews/NN-<thema>.md`.
5. **Ausbessern:** `implementer` arbeitet die Befunde ab und hakt sie in der Review-Datei ab.
6. **Abnahme:** Hauptsession (Opus) prüft gegen Plan und ADRs, dann PR und Squash-Merge.
- Subagent `chore` (Haiku) nur für Mechanisches: Testdaten, Beispieldateien, Doku-Formatierung, Lint-Fixes.

## Git-Workflow (ADR 0005)

- Nie direkt auf `master` committen oder pushen. Jeder Plan-Schritt bekommt einen eigenen Branch,
  benannt nach Typ und Schritt: `feat/03-calculation`, `docs/01-architecture`, `chore/<thema>`.
- Ein PR pro Schritt. Der PR-Titel ist eine Conventional-Commit-Nachricht, denn mit Squash-Merge wird
  er zum einzigen Commit auf `master`.
- Der PR verlinkt Plan-Schritt und Review-Datei (`.github/pull_request_template.md`).
- Gemergt wird nur, wenn die Checks grün sind und der Mensch freigegeben hat. Danach wird der Branch gelöscht.
- Kein Force-Push, kein `--no-verify`, keine Merge-Commits.
- Version nur per Bump-Skript und nur auf Anweisung des Menschen, Releases startet nur der Mensch (ADR 0006).

## Definition of Done (pro Schritt)

- ruff, pyright, pytest grün
- Neue Logik hat Tests, Berechnungen haben mindestens einen Golden-Test mit Handrechnung
- Plan-Datei aktualisiert (erledigt / verschoben)
- Ein Squash-Merge pro Schritt, Conventional Commits (`feat:`, `test:`, `docs:`, `chore:`)
