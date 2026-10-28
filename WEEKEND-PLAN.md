# Wochenendplan: carbon-preaudit

Ziel bis Sonntagabend: Berechnungslauf + Pre-Audit-Check, mit Evals, einer Seite und einer Repo-Historie,
die den Ablauf Planen → Umsetzen → Prüfen → Review → Ausbessern zeigt.

**Abbruchregel:** Liegst du hinter dem Plan, streiche in dieser Reihenfolge: Karte → Docker → Speicherung der Läufe.
Berechnung, Pre-Audit, Evals und README werden nie gestrichen.

---

## Freitagabend: Setup (30 min, manuell)

```bash
git clone <dein-repo> && cd carbon-preaudit
# CLAUDE.md, .claude/agents/ und docs/ aus dem Starter-Kit hineinkopieren
echo "ANTHROPIC_API_KEY=" > .env && echo ".env" >> .gitignore
git add -A && git commit -m "chore: add agent setup and project brief"
claude --model opus
```

In Claude Code: `/agents` aufrufen und prüfen, dass `implementer`, `reviewer`, `chore` erscheinen.
Steht `fable` in deinem Zugang nicht zur Verfügung, in `reviewer.md` auf `opus` umstellen.

---

## Samstag

### 1. Architektur planen · Opus · 45 min

Plan Mode aktivieren (Shift+Tab), dann:

> Lies CLAUDE.md. Schreibe docs/plans/01-architecture.md mit: Modulübersicht, Domänenmodelle
> (Felder mit Typen und Einheiten), Ablauf eines Berechnungslaufs und eines Pre-Audits als
> Mermaid-Diagramm, und den Umsetzungsschritten 02 bis 07 mit je einer Definition of Done.
> Schreibe außerdem drei ADRs nach docs/adr/ im Format Kontext/Entscheidung/Konsequenzen:
> 0001 KI extrahiert, Code bewertet · 0002 Reproduzierbare Läufe über Hash ·
> 0003 SQLite statt Postgres für die Demo. Noch keinen Code.

**Checkpoint:** Du liest Plan und ADRs, korrigierst, gibst frei. Commit `docs: architecture plan and ADRs`.

### 2. Projektgerüst · Sonnet + Haiku · 45 min

> Use the implementer agent for step 02 in docs/plans/01-architecture.md: uv-Projekt, ruff, pyright strict,
> pytest, FastAPI mit /health, Dockerfile, GitHub Actions (ruff, pyright, pytest).

> Use the chore agent: Lege unter examples/ an: ein GeoJSON-Polygon von ca. 100 ha in Costa Rica,
> eine CSV mit 3 Plots à 400 m² und je 8 bis 12 Bäumen mit realistischen Werten
> (dbh_cm 5–40, height_m 3–25, wood_density 0.4–0.7).

**Checkpoint:** CI grün auf GitHub. Commit.

### 3. Berechnungslauf · Sonnet · 2,5 h

> Use the implementer agent for step 03: calc/ mit Fläche (pyproj.Geod), Allometrie, CO₂e,
> Puffer, params.py mit PARAMS_VERSION, Hash über kanonische Eingaben + PARAMS_VERSION + Code-Version.
> Tests: Golden-Test mit Handrechnung für einen Baum und einen Plot, Hash bleibt bei
> umsortierten CSV-Zeilen gleich und ändert sich bei geändertem Parameter.

**Checkpoint:** Tests grün, Ergebnis für examples/ plausibel. Commit `feat: reproducible calculation run`.

### 4. Review 1 · Fable → Sonnet → Opus · 1 h

> Use the reviewer agent on step 03.

> Use the implementer agent to work through docs/reviews/03-calculation.md.

Danach in der Hauptsession (Opus):

> Prüfe docs/reviews/03-calculation.md: Sind alle kritischen und wichtigen Befunde sauber gelöst?
> Stimmt der Code mit ADR 0002 überein? Nenne Abweichungen, ändere nichts.

**Checkpoint:** Commit `fix: address review 03`.

---

## Sonntag

### 5. Pre-Audit · Sonnet · 2 h

> Use the implementer agent for step 05: domain ClaimedValues und Finding, Extractor-Protocol,
> AnthropicExtractor mit strukturierter Ausgabe (Modell per Umgebungsvariable), FakeExtractor,
> compare.py mit Toleranzen aus CLAUDE.md. Fehlt ein Wert im Text, ist das ein Befund vom Typ „hinweis“.
> Jeder Befund trägt das wörtliche Zitat. Tests nur mit FakeExtractor.

**Checkpoint:** Commit `feat: pre-audit extraction and comparison`.

### 6. Evals · Haiku + Sonnet · 1,5 h

> Use the chore agent: Lege unter evals/cases/ 12 YAML-Fälle an. Jeder Fall: ein PDD-Abschnitt
> (120–200 Wörter, Englisch) auf Basis der Werte aus examples/, und `expected_findings`.
> Verteilung: 3 fehlerfrei, 3 falsche Fläche, 2 falsche Tonnen, 2 falscher Puffer,
> 2 fehlender Wert. Fehler unauffällig in den Fließtext einbauen.

> Use the implementer agent for step 06: evals/ Runner und Scorer (Precision, Recall je Feld),
> Ergebnis als Markdown-Tabelle nach evals/results/latest.md.

Dann manuell: `uv run python -m evals`. **Checkpoint:** Ergebnis committen, auch wenn es nicht perfekt ist.

### 7. Review 2 · Fable → Sonnet · 45 min

> Use the reviewer agent on steps 05 and 06. Prüfe besonders, ob das LLM irgendwo bewertet statt nur extrahiert.

> Use the implementer agent to work through docs/reviews/05-preaudit.md.

### 8. Oberfläche · Sonnet · 1,5 h

> Use the implementer agent for step 07: eine Seite mit HTMX. Upload GeoJSON + CSV + PDD-Text.
> Links: Leaflet-Karte mit Polygon, darunter Kennzahlen (ha, tCO₂e brutto/netto, Puffer, Hash gekürzt).
> Rechts: PDD-Text, Zitate aus Befunden farbig markiert, darunter die Befundliste.
> Schlicht, gut lesbar, funktioniert ohne Build-Schritt.

### 9. Abschluss · Opus · 45 min

> Schreibe die README auf Deutsch: Problem in drei Sätzen, Screenshot-Platzhalter,
> Architektur als Mermaid, Leitprinzipien mit Verweis auf die ADRs, Eval-Ergebnis aus
> evals/results/latest.md, Abschnitt „So wurde gebaut“ (Agenten, Modelle, Ablauf, Verweis auf
> docs/plans und docs/reviews), Abschnitt „Bewusst nicht enthalten“ mit je einem Satz,
> wie es anschließen würde, und Quickstart.

Manuell: Screenshot oder GIF aufnehmen, einfügen, letzter Commit.

---

## Was der Reviewer im Repo sehen soll

| Ort | Zeigt |
| --- | --- |
| `.claude/agents/` | Rollen und Modellwahl |
| `docs/plans/` | Planung vor Code |
| `docs/adr/` | Begründete Entscheidungen |
| `docs/reviews/` | Unabhängige Prüfung und wie Befunde gelöst wurden |
| `evals/results/` | KI-Qualität gemessen, nicht behauptet |
| Git-Historie | Ein Commit pro Schritt, der Ablauf ist nachvollziehbar |
