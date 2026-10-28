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
  (`wood_density` in g/cm³, optional, Default aus Parametern)
- Berechnungslauf:
  - Fläche in ha (geodätisch, `pyproj.Geod`)
  - Oberirdische Biomasse je Baum: Chave et al. 2014, `AGB_kg = 0.0673 * (ρ * D² * H) ** 0.976`
  - Kohlenstoff = Biomasse × 0.47, CO₂e = C × 44/12
  - Mittelwert tCO₂e/ha über alle Plots, hochgerechnet auf die Fläche
  - Pufferabzug (Default 20 %), Ergebnis = handelbare tCO₂e
  - Alle Konstanten in `src/carbon_preaudit/calc/params.py` mit `PARAMS_VERSION`
- Pre-Audit:
  - LLM extrahiert `ClaimedValues` (area_ha, tco2e_gross, tco2e_net, buffer_pct, methodology),
    jeweils mit wörtlichem Zitat oder `null`
  - Deterministischer Abgleich mit Toleranzen (Fläche 1 %, Tonnen 2 %, Puffer exakt)
  - Ergebnis: Liste von `Finding`
- Evals: Testfälle mit absichtlich eingebauten Fehlern, Metriken Precision/Recall
- Eine Weboberfläche: Karte, Kennzahlen, markierter Text, Befundliste

## Bewusst nicht im Scope

Methodologiekonforme Berechnung (VM0047), Unsicherheitsabzüge, Leakage, PDD-Generierung,
RAG über Methodologien, Satellitendaten, Mandanten/Login, Postgres/PostGIS.
Diese Punkte landen nur im README-Abschnitt „Bewusst nicht enthalten“.

## Stack

- Python 3.12, **uv** (kein pip, kein poetry)
- **ruff** (Lint + Format), **pyright** (strict für `src/`), **pytest**
- FastAPI, Pydantic v2, Jinja2 + HTMX, Leaflet (beides per CDN, Version gepinnt)
- SQLAlchemy 2 mit SQLite (ADR begründet den späteren Wechsel zu Postgres)
- Anthropic Python SDK hinter eigener Schnittstelle `Extractor` (Protocol); kein LangChain
- Docker (ein Dockerfile), GitHub Actions

## Befehle

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest
uv run uvicorn carbon_preaudit.web.app:app --reload
uv run python -m evals            # braucht ANTHROPIC_API_KEY
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
```

## Code-Konventionen

- Bezeichner, Docstrings und Commits auf Englisch; Doku in `docs/` und README auf Deutsch
- Type Hints überall, keine `Any` in `src/`
- Reine Funktionen in `calc/` und `preaudit/compare.py`, keine I/O dort
- Kein Netzwerkzugriff in Unit-Tests: immer `FakeExtractor`
- Fehler als eigene Exception-Klassen, keine nackten `except`

## Arbeitsweise mit Agenten

1. **Planen:** Hauptsession (Opus) schreibt Plan nach `docs/plans/NN-<thema>.md`. Mensch gibt frei.
2. **Umsetzen:** Subagent `implementer` (Sonnet) setzt genau einen Plan-Schritt um.
3. **Prüfen:** ruff, pyright, pytest müssen grün sein, bevor ein Review startet.
4. **Review:** Subagent `reviewer` (Fable) schreibt Befunde nach `docs/reviews/NN-<thema>.md`.
5. **Ausbessern:** `implementer` arbeitet die Befunde ab und hakt sie in der Review-Datei ab.
6. **Abnahme:** Hauptsession (Opus) prüft gegen Plan und ADRs, dann Commit.
- Subagent `chore` (Haiku) nur für Mechanisches: Testdaten, Beispieldateien, Doku-Formatierung, Lint-Fixes.

## Definition of Done (pro Schritt)

- ruff, pyright, pytest grün
- Neue Logik hat Tests, Berechnungen haben mindestens einen Golden-Test mit Handrechnung
- Plan-Datei aktualisiert (erledigt / verschoben)
- Ein Commit pro Schritt, Conventional Commits (`feat:`, `test:`, `docs:`, `chore:`)
