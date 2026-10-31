# Audit-Zusammenfassung

## Überblick

Das Audit ergab 31 Findings (3 hoch, 6 mittel, 22 niedrig), dazu kam bei der Korrektur F-32. Der Mensch
hat am 2026-10-31 alle 31 mit Ansatz (a) freigegeben und F-14 und F-15 zurückgestellt, weil sie echte
API-Läufe brauchen. Korrigiert sind 29 Findings, jedes in einem eigenen Commit. F-32 ist neu und nicht
korrigiert. Tests, Lint und Typecheck sind vor und nach der Korrektur grün.

## Findings nach Kategorie

| Kategorie | Gefunden | Freigegeben | Korrigiert | Nicht korrigiert / zurückgestellt |
|-----------|----------|-------------|------------|-----------------------------------|
| K1 | 1 | 1 | 1 | 0 |
| K2 | 1 | 1 | 1 | 0 |
| K3 | 8 | 8 | 8 | 0 |
| K4 | 3 | 3 | 3 | 0 |
| K5 | 0 | 0 | 0 | 0 |
| K6 | 5 | 5 | 5 | 0 |
| K7 | 3 | 3 | 2 | 1 (F-14 zurückgestellt) |
| K8 | 3 | 2 | 1 | 2 (F-15 zurückgestellt, F-32 offen) |
| K9 | 1 | 1 | 1 | 0 |
| K10 | 1 | 1 | 1 | 0 |
| K11 | 5 | 5 | 5 | 0 |
| K12 | 1 | 1 | 1 | 0 |
| **gesamt** | **32** | **31** | **29** | **3** |

## Korrigiert (laut Freigabe)

Commit-Scope kleingeschrieben (`fix(f-1)`), weil commitlint `scope-case: lower-case` verlangt.

- F-1 – `TypeError` als Extraktionsfehler – `dc16cde` – Nachweis: neuer Test, dass ein `TypeError` im Aufruf
  durchschlägt; fehlende Zugangsdaten werden beim Erzeugen geprüft (Test mit Stub ohne `auth_headers`).
- F-2 – Ignore-Kommentar ohne Wirkung – `9295dd9` – Nachweis: pyright weiter 0 Fehler.
- F-3 – Assertions über Literale – `445b4ae` – Nachweis: Rechnung aus den Konstanten, Test grün.
- F-4 – `.claude/settings.json` mit Firmenname – `93c22ef` – Nachweis: `git ls-files .claude` ohne die
  Datei, Eintrag in `.gitignore`, lokale Datei vorhanden.
- F-5 – `.claude/launch.json` – `89f13c3` – Nachweis wie F-4.
- F-6 – Refactoring im UI-Commit – `c88f9f3` – Nachweis: Nachtrag in `docs/reviews/07-ui.md`.
- F-7 – `_M2_PER_HA` doppelt – `142f85d` – Nachweis: eine Definition in `area.py`, Golden-Tests grün.
- F-8 – Feldliste mehrfach – `25975f9` – Nachweis: `scorer.py` und `highlight.py` nutzen `FIELD_ORDER`.
- F-9 – Ringprüfung doppelt – `4d63877` – Nachweis: Begründung im Docstring von `GeoJSONPolygon`.
- F-10 – Default-Modell doppelt abgeleitet – `7705b7f` – Nachweis: Extractors haben `model`, Runner-Test.
- F-11 – Englische Meldungen in der Oberfläche – `a15d69a` – Nachweis: Web-Test prüft deutschen Satz.
- F-12 – `httpx2` nur dev – `3aea9ca` – Nachweis: in `[project] dependencies`, Container baut.
- F-13 – `markupsafe` nicht deklariert – `d956d15` – Nachweis wie F-12.
- F-16 – CLAUDE.md-Struktur veraltet – `195d273` – Nachweis: Diff.
- F-17 – README-Abschnitt fehlt – `08df975` – Nachweis: Abschnitt „Bewusst nicht enthalten“.
- F-18 – Widersprüchliche Versionsregel – `88e1c3b` – Nachweis: gleiche Formulierung in CLAUDE.md und
  `version.py`, passend zu ADR 0002.
- F-19 – HTTP 500 bei Rechenfehlern – `aac15e6` – Nachweis: neuer Web-Test, rot ohne Fix (500), grün mit Fix
  (422).
- F-20 – Mehrdeutige Zahlenlesart – `b2921f5` – Nachweis: neue Tests zum Zahlenformat und zum Fall `clean-03`
  aus dem ersten Eval-Lauf (Fehllesung 8,364 ergibt jetzt `info` statt `critical`); Eval-Konsistenztest grün.
- F-21 – Kein Zugriffsschutz – `ddeed97` – Nachweis: README-Hinweis, Port nur an `127.0.0.1`.
- F-22 – Client pro Anfrage – `6a8318b` – Nachweis: Test, dass die Fabrik einmal aufgerufen wird.
- F-23 – Mehrfache Git-Aufrufe – `9cdf3f7` – Nachweis: Testlaufzeit gesamt von rund 33 s auf rund 15 s.
- F-24 – `sqlalchemy` unbenutzt – `5a8aef2` – Nachweis: aus `pyproject.toml` und `uv.lock` entfernt.
- F-25 – Extractor-Tests je Anbieter doppelt – `96f7cd0` – Nachweis: alle Fehlerzweige beider Extractors
  weiter durch Tests ausgeführt (Zweige einzeln gegen den Code abgeglichen).
- F-26 – Prompt-Wortlaut-Tests – `6862f10` – Nachweis: entfernt; der Prompt-Hash steht im Eval-Bericht.
- F-27 – Belegregeln dreifach – `3e148a8` – Nachweis: Regeln in `tests/test_evidence_span.py`.
- F-28 – Parserfehler über Web doppelt – `e6c29ac` – Nachweis: ein Web-Test für Parserfehler, einer für
  Rechenfehler (F-19).
- F-29 – Pydantic-Verhalten je Feld – `1a1a660` – Nachweis: nur eigene Validatoren getestet.
- F-30 – Beispieldaten fünffach – `c68a695` – Nachweis: End-to-end aus `test_compare.py` entfernt.
- F-31 – Tests ohne Aussage – `9553a70` – Nachweis: zwei entfernt, drei parametrisiert.

## Freigegeben, aber nicht abgeschlossen

- F-14 – Anthropic-Pfad nie live – zurückgestellt, braucht `ANTHROPIC_API_KEY`.
- F-15 – Commit-Angabe im Eval-Bericht – zurückgestellt, braucht einen neuen Eval-Lauf mit `GEMINI_API_KEY`.

## Neu entdeckt während der Korrektur

- F-32 – Container-Start laut README ohne API-Key – Entscheidung offen.

## Verhaltensänderungen

- F-1 – Ein `TypeError` im Anthropic-Aufruf wird nicht mehr als Extraktionsfehler gemeldet; fehlende
  Zugangsdaten werden schon beim Erzeugen des Extractors erkannt.
- F-4, F-5 – Projekt-Hooks, Berechtigungen und Startkonfiguration aus `.claude/` gelten für neue Klone nicht
  mehr; lokal bleiben die Dateien bestehen.
- F-11 – Fehlermeldungen in der Oberfläche beginnen mit einem deutschen Satz, die englische Meldung folgt als
  „Details“.
- F-19 – Rechenfehler liefern 422 mit Meldung statt 500.
- F-20 – In einem Text mit erkennbarem Zahlenformat gilt nur noch dessen Lesart; eine Fehllesung ergibt
  `info` „Wert nicht im Zitat belegt“ statt einer Abweichung.
- F-21 – Der dokumentierte Container-Start bindet nur an `127.0.0.1`.

## Baseline-Vergleich

| Messgröße | vorher | nachher |
|---|---|---|
| Tests | 332 passed | 324 passed |
| Testfunktionen | 225 | 189 |
| Zeilen Tests | 2 785 | 2 507 |
| Zeilen Code (`src`, `evals`, `tools`) | 2 225 | 2 303 |
| Laufzeit pytest | rund 33 s | rund 15 s |
| ruff check | All checks passed | All checks passed |
| ruff format | 74 files formatted | 77 files formatted |
| pyright | 0 errors | 0 errors |

Neu grün: keine (vorher war alles grün). Neu rot: keine. Die Zahl der gesammelten Tests sinkt nur um 8,
weil neue Tests für F-1, F-19, F-20 und F-22 dazukamen und die Extractor-Fehlerfälle jetzt als Parameter
gezählt werden (16 Fälle in einer Funktion). Die Zahl der Testfunktionen sinkt um 36, die Testzeilen um 278.

## Nicht verifiziert

- F-25 – Abdeckung der Extractor-Zweige nur durch Lesen abgeglichen; kein Coverage-Werkzeug installiert.
- F-20 – Wirkung auf die echte Extraktion nicht gemessen; ein Eval-Lauf mit Key steht aus (siehe F-15).
- F-11 – Darstellung der Meldungen nur über den TestClient geprüft, nicht im Browser.
- Container: gebaut, `/health` und `/example` liefern 200; `POST /check` im Container nicht geprüft (F-32).

## Getroffene Annahmen

- Für F-7 ist „gemeinsames Modul“ `calc/area.py`, nicht `params.py`, damit `PARAMS_VERSION` unverändert bleibt.
- Für F-30 bleibt `tests/test_examples_run.py`, weil die DoD von Schritt 03 „Lauf über `examples/` liefert
  plausible Werte“ verlangt.
- Für F-21 ist die Bindung an `127.0.0.1` Teil von „Betrieb nur lokal dokumentieren“.
