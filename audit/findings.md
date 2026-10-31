# Findings

Stand: `master` bei `2b61939`, Baseline siehe `audit/baseline.md`. Geordnet nach Kategorie, innerhalb der
Kategorie nach Fundort. Der Schweregrad stuft die Auswirkung ein, er ist keine Priorisierung.

## Übersicht

| Kategorie | Anzahl | kritisch | hoch | mittel | niedrig | davon „zu prüfen“ |
|-----------|--------|----------|------|--------|---------|-------------------|
| K1 Verschluckte Fehler, stille Fallbacks | 1 | 0 | 0 | 1 | 0 | 0 |
| K2 Symptome statt Ursachen | 1 | 0 | 0 | 0 | 1 | 1 |
| K3 Reward Hacking, schwache Tests | 9 | 0 | 0 | 1 | 8 | 0 |
| K4 Scope Creep | 3 | 0 | 1 | 0 | 2 | 0 |
| K5 Over-Engineering | 0 | 0 | 0 | 0 | 0 | 0 |
| K6 Duplikation | 5 | 0 | 0 | 0 | 5 | 1 |
| K7 Halluzinierte oder veraltete APIs, Packages | 3 | 0 | 0 | 2 | 1 | 1 |
| K8 Unbelegte Erfolgsbehauptungen | 3 | 0 | 0 | 2 | 1 | 0 |
| K9 Unvollständige Implementierungen | 1 | 0 | 0 | 0 | 1 | 0 |
| K10 Kontextverlust | 1 | 0 | 0 | 0 | 1 | 1 |
| K11 Security, Performance, Edge Cases | 5 | 0 | 2 | 1 | 2 | 1 |
| K12 Unnötige Dependencies, Rauschen | 1 | 0 | 0 | 0 | 1 | 0 |
| **gesamt** | **33** | **0** | **3** | **7** | **23** | **5** |

## K1 – Verschluckte Fehler und stille Fallbacks

### F-1 – `TypeError` beim Anthropic-Aufruf wird als Extraktionsfehler gemeldet
- Kategorie: K1
- Ort: `src/carbon_preaudit/preaudit/extractor.py:159-161`
- Schweregrad: mittel
- Sicherheit: wahrscheinlich
- Beleg: `except (anthropic.AnthropicError, TypeError) as e: raise ExtractionError(...)` um den gesamten
  Aufruf `self._client.beta.messages.create(...)`. Der Kommentar begründet das mit fehlendem API-Key.
- Auswirkung: Jeder `TypeError` innerhalb des Aufrufs, auch ein Programmierfehler wie ein falscher
  Parametername oder -typ nach einem SDK-Update, erscheint als „Anthropic API call failed“ und in der
  Oberfläche als Hinweis, nicht als Fehler im Code.
- Möglicher Korrekturansatz: (a) Key-Prüfung vor dem Aufruf, `TypeError` nicht mehr fangen. (b) `TypeError`
  nur fangen, wenn die Meldung auf fehlende Authentifizierung verweist. (c) Client-Erzeugung und Aufruf
  getrennt absichern.
- Verhaltensänderung bei Korrektur: ja (Programmierfehler würden als Exception sichtbar)
- Abhängigkeiten: keine
- Aufwand: S

## K2 – Symptome statt Ursachen

### F-2 – Ignore-Kommentar für eine Regel, die pyright nicht kennt
- Kategorie: K2
- Ort: `evals/cases.py:41`
- Schweregrad: niedrig
- Sicherheit: zu prüfen
- Beleg: `raw: object = yaml.safe_load(...)  # pyright: ignore[reportAny]`. `reportAny` ist eine Regel von
  basedpyright, das Projekt nutzt pyright 1.1.414. Eine Testdatei mit demselben Kommentar meldet in pyright
  0 Fehler und 0 Warnungen, der Kommentar hat also keine erkennbare Wirkung.
- Auswirkung: Der Kommentar suggeriert eine unterdrückte Prüfung, die es nicht gibt.
- Möglicher Korrekturansatz: Kommentar entfernen, oder die gemeinte pyright-Regel eintragen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

## K3 – Reward Hacking und schwache Tests

### F-3 – Assertions über Literale statt über das System
- Kategorie: K3
- Ort: `tests/test_extractor.py:478-479`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `assert 2.0 * 2.0**2 + 1.0 < 10.0` und `assert (2.0 + 4.0 + 8.0) + 3 * 1.0 == 17.0`. Beide
  Ausdrücke enthalten nur Zahlenliterale.
- Auswirkung: Die Zeilen sind immer wahr und prüfen weder die Retry-Konstanten noch das SDK-Verhalten. Sie
  dokumentieren eine Rechnung, ohne sie am Code zu binden.
- Möglicher Korrekturansatz: Rechnung aus den Konstanten `GEMINI_RETRY_*` ableiten, oder die Zeilen als
  Kommentar führen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

### F-25 – Extractor-Tests je Anbieter doppelt geschrieben
- Kategorie: K3
- Ort: `tests/test_extractor.py:100-264` (Anthropic) und `:322-481` (Gemini)
- Schweregrad: mittel
- Sicherheit: belegt
- Beleg: 37 Testfunktionen auf 481 Zeilen. Rund zwölf Fälle existieren je Anbieter als eigene Funktion mit
  eigenem Fake: Erfolg, Request-Parameter, Modell aus Umgebung, `extracted_by`, Ablehnung bzw. Blockierung,
  Abbruch bei Token-Limit, ungültiges JSON, inkonsistente Ausgabe, API-Fehler, SDK-Fehler, fehlender Key,
  Closing-Tag. Zusätzlich prüfen `test_closing_tag_in_text_is_defused` und
  `test_closing_tag_variants_are_defused` dieselbe Funktion `_document`.
- Auswirkung: Viel Text für dieselbe Fehlerabbildung; Änderungen an der gemeinsamen Logik müssen an zwei
  Stellen nachgezogen werden. Die Tests sind einzeln lesbar, in Summe aber schwer zu überblicken.
- Möglicher Korrekturansatz: (a) Gemeinsame Fälle über den Anbieter parametrisieren, anbieterspezifische
  (Request-Parameter, Retry-Optionen) einzeln lassen. (b) Je Anbieter nur Erfolg, Request und je einen
  Fehlerpfad behalten, die übrigen Fehlerpfade einmal zentral.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: F-26
- Aufwand: M

### F-26 – Tests prüfen den Wortlaut des Prompts
- Kategorie: K3
- Ort: `tests/test_extractor.py:238-264`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `test_prompt_states_the_rules` und `test_prompt_is_unit_neutral_and_keeps_tc_amounts` prüfen, ob
  Teilstrings wie „character by character“ in `SYSTEM_PROMPT` stehen.
- Auswirkung: Spiegeltest: Die erwarteten Werte stammen aus dem Prompt selbst. Ob das Modell die Regeln
  befolgt, prüfen nur die Evals; jede Umformulierung macht den Test rot, ohne dass sich Verhalten ändert.
- Möglicher Korrekturansatz: Tests entfernen und auf den Prompt-Hash im Eval-Bericht verlassen, oder auf
  einen einzigen Test für die Sicherheitsregel („data, not instructions“) reduzieren.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: F-25
- Aufwand: S

### F-27 – Zitat- und Belegregeln in drei Testdateien
- Kategorie: K3
- Ort: `tests/test_compare.py:218-245, 488-532`, `tests/test_evidence_span.py:8-37`,
  `tests/test_highlight.py:55-60, 82-90`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: Wortgrenzen, Mindestwortzahl, Zeilenumbruch und „Zahl in längerer Zahl“ werden in `test_compare.py`
  über `compare()`, in `test_evidence_span.py` über `evidence_span()` und in `test_highlight.py` über die
  Markierung geprüft. Beispiel „0 ha“ in „100.0 ha“: `test_compare.py:496` und `test_evidence_span.py:8`.
- Auswirkung: Dieselbe Regel steht dreimal; bei einer Regeländerung sind drei Dateien anzupassen.
- Möglicher Korrekturansatz: Regeln einmal an `evidence_span` testen; in `compare` und `highlight` nur je
  einen Test, dass die Funktion verwendet wird.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

### F-28 – Parserfehler über die Weboberfläche erneut getestet
- Kategorie: K3
- Ort: `tests/test_web.py:138-160, 237-248`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: Kaputtes GeoJSON, fehlende CSV-Spalte und das CSV-Feldlimit sind in `tests/test_inputs.py` getestet
  und zusätzlich je einzeln über `POST /check`.
- Auswirkung: Die Oberfläche hat genau einen Fehlerpfad (`InputError` → 422); er wird mehrfach mit
  unterschiedlichen Ursachen geprüft.
- Möglicher Korrekturansatz: Einen Web-Test für „InputError ergibt 422 mit Meldung“ behalten, die übrigen
  Ursachen nur in `test_inputs.py`.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: F-19 (der Web-Test zu Rechenfehlern käme hinzu)
- Aufwand: S

### F-29 – Pydantic-Verhalten Feld für Feld getestet
- Kategorie: K3
- Ort: `tests/test_inputs.py:229-270`, `tests/test_preaudit_models.py:7-47`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `test_models_reject_non_finite_floats` prüft für neun Felder einzeln, dass `allow_inf_nan=False`
  wirkt; `test_preaudit_models.py` prüft unter anderem, dass `frozen=True` Zuweisungen verhindert und dass
  ein `Literal` fremde Werte ablehnt.
- Auswirkung: Getestet wird überwiegend die Bibliothek, nicht eigene Logik. Eigene Validatoren
  (`_both_or_neither`, `_trees_consistent`) sind darunter und haben Aussagekraft.
- Möglicher Korrekturansatz: Tests auf eigene Validatoren beschränken; Framework-Einstellungen nicht je Feld
  testen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

### F-30 – Beispieldaten an fünf Stellen end-to-end geprüft
- Kategorie: K3
- Ort: `tests/test_examples_run.py`, `tests/test_compare.py:378-425`, `tests/test_web.py:89-128`,
  `tests/test_evals_cases_consistency.py`, `tests/test_calc_golden.py`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `examples/` wird in `test_examples_run.py` (Plausibilität), `test_compare.py` (zwei End-to-end-Fälle
  mit eigenen `_example_run`/`_correct_claims`), `test_web.py` (tC-Fall und fehlerfreier Fall) und indirekt
  in der Eval-Konsistenz (12 Fälle) gerechnet. Die Hilfsfunktion für den Beispiel-Lauf existiert in
  `test_compare.py:378` und `evals/runner.py:55` getrennt.
- Auswirkung: Der tC-Fall ist dreimal abgedeckt (compare, web, Eval-Fall `tonnes-tc-01`).
- Möglicher Korrekturansatz: End-to-end über Beispieldaten einmal in der Eval-Konsistenz und einmal in der
  Oberfläche; `test_compare.py` ohne Beispieldaten.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

### F-31 – Tests ohne eigene Aussage
- Kategorie: K3
- Ort: `tests/test_compare.py:370-372`, `tests/test_inputs.py:139-141`, `tests/test_inputs.py:44-60`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `test_compare_is_deterministic` ruft eine reine Funktion zweimal auf und vergleicht.
  `test_all_errors_share_base_class` prüft einen einzigen Fall, den jeder andere Fehlertest bereits abdeckt,
  weil alle mit Unterklassen von `InputError` arbeiten. `test_feature_is_rejected`,
  `test_feature_collection_is_rejected`, `test_multipolygon_is_rejected` sind drei nahezu identische
  Funktionen.
- Auswirkung: Zahl der Tests steigt ohne zusätzlichen Erkenntnisgewinn.
- Möglicher Korrekturansatz: Die beiden ersten entfernen, die drei Geometrietypen parametrisieren.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

### F-33 – Parametertabellen mit vielen gleichartigen Fällen
- Kategorie: K3
- Ort: `tests/test_compare.py` (`test_number_candidates`, `test_value_found_in_quote`, weitere),
  `tests/test_inputs.py`, `tests/test_bump_script.py`, `tests/test_evals_cases.py`, `tests/test_hash.py`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: Nach F-25 bis F-31 zählte pytest weiter 324 Tests, davon rund 130 Zeilen in Parametertabellen.
  Beispiele: 18 Fälle für `number_candidates`, 15 für „Wert im Zitat“ (fast alle Varianten derselben
  Zahlenlesung, die `number_candidates` bereits prüft), 11 ungültige CSV-Zahlen, 10 ungültige Versionen.
  Aufgenommen auf Hinweis des Menschen („über 300 Tests für diese Menge Code“).
- Auswirkung: Viele Zeilen prüfen dieselbe Regel mit anderen Zahlen; die Zahl der Tests sagt wenig über
  die Abdeckung aus.
- Möglicher Korrekturansatz: (a) Je Regel bzw. Code-Zweig ein Fall, Grenzfälle behalten; über `compare()`
  nur noch die Integration, Zahlenlesung allein an `number_candidates`.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: F-25 bis F-31
- Aufwand: S

## K4 – Scope Creep

### F-4 – Lokale Claude-Konfiguration mit Firmenname im Gemini-Commit
- Kategorie: K4
- Ort: `.claude/settings.json:80`, eingeführt mit `1e24220 feat: add gemini extractor as default provider (#8)`
- Schweregrad: hoch
- Sicherheit: belegt
- Beleg: Der Commit ändert neben dem Extractor auch `.claude/settings.json` (83 Zeilen), ohne Bezug zum
  Commit-Zweck. Zeile 80 enthält einen Plugin-Eintrag mit Firmennamen (`"…-guardrails@…": true`). Das Repo
  ist öffentlich. Die Projektregel aus Schritt 1 lautet „Kein Firmenname im Repo“. Die Datei enthält außerdem
  Statuszeile, Plugin-Liste und Telemetrie-Einstellungen der lokalen Umgebung. Keine Secrets.
- Auswirkung: Ein Firmenbezug ist öffentlich sichtbar, entgegen der ausdrücklichen Regel. Die Historie auf
  GitHub enthält ihn auch nach einer Korrektur am Dateistand.
- Möglicher Korrekturansatz: (a) Datei aus dem Repo nehmen und in `.gitignore` aufnehmen. (b) Nur die
  Plugin-Zeile entfernen. (c) Zusätzlich die Historie bereinigen; das erfordert Force-Push und widerspricht
  ADR 0005, daher nur auf ausdrückliche Entscheidung.
- Verhaltensänderung bei Korrektur: ja (bei (a): Projekt-Hooks und -Berechtigungen gelten für andere
  Klone nicht mehr)
- Abhängigkeiten: F-5
- Aufwand: S (ohne Historie), M (mit Historie)

### F-5 – Lokale Startkonfiguration im UI-Commit
- Kategorie: K4
- Ort: `.claude/launch.json`, eingeführt mit `01f911a feat: add web ui … (#10)`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: Der Commit enthält `.claude/launch.json` (Startbefehl für den Server im Browser-Pane der Desktop-App).
  Im PR war die Datei nicht als Teil des Schritts vorgesehen.
- Auswirkung: Werkzeugspezifische lokale Konfiguration liegt im Repo; sie startet den Server mit
  `--env-file .env`.
- Möglicher Korrekturansatz: Datei entfernen und ignorieren, oder sie als bewusst geteilte Konfiguration
  dokumentieren.
- Verhaltensänderung bei Korrektur: nein (für den Code)
- Abhängigkeiten: F-4
- Aufwand: S

### F-6 – Umbenennung öffentlicher Funktionen in `compare.py` im UI-Commit
- Kategorie: K4
- Ort: `src/carbon_preaudit/preaudit/compare.py`, Commit `01f911a`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: Der Commit „add web ui …“ benennt `_squash`, `_de`, `_quote_in_text`, `_LABELS` in öffentliche Namen
  um und führt `evidence_span` und `squash_with_offsets` ein (62 geänderte Zeilen in `compare.py`).
  Review 07 hat das als verhaltensneutral geprüft.
- Auswirkung: Ein Refactoring der Vergleichslogik steckt in einem Feature-Commit der Oberfläche; im
  Squash-Commit auf `master` ist es nicht getrennt nachvollziehbar.
- Möglicher Korrekturansatz: keine Codeänderung nötig; ggf. im Plan oder in der Review-Datei vermerken.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

## K5 – Over-Engineering

Geprüft: `Extractor`-Protocol (drei Implementierungen), `make_extractor` (zwei Anbieter), `_LazyExtractor`
(begründet im Docstring), Workspace-Paket `tools/`. Kein Finding.

## K6 – Duplikation statt Wiederverwendung

### F-7 – Konstante `_M2_PER_HA` doppelt
- Kategorie: K6
- Ort: `src/carbon_preaudit/calc/area.py:10`, `src/carbon_preaudit/calc/run.py:12`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `_M2_PER_HA = 10_000.0` in beiden Modulen.
- Auswirkung: Zwei Definitionen derselben Umrechnung; heute identisch.
- Möglicher Korrekturansatz: eine Definition, z. B. in `calc/params.py` oder einem gemeinsamen Modul.
  In `params.py` wäre es ein Parameterwert mit Folgen für `PARAMS_VERSION`/`PARAMS_GOLDEN`.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: ggf. `PARAMS_VERSION` (ADR 0002)
- Aufwand: S

### F-8 – Liste der fünf Felder an mehreren Stellen
- Kategorie: K6
- Ort: `src/carbon_preaudit/domain/models.py:160-162` (`FindingField`),
  `src/carbon_preaudit/preaudit/compare.py:23-29` (`FIELD_ORDER`), `evals/scorer.py:10-16` (`FIELDS`),
  `src/carbon_preaudit/web/highlight.py:38-44` (Dict der Claims)
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: Vier unabhängige Aufzählungen derselben fünf Feldnamen.
- Auswirkung: Ein neues Feld muss an vier Stellen ergänzt werden; pyright erkennt eine fehlende Stelle nur
  teilweise.
- Möglicher Korrekturansatz: `FIELD_ORDER` aus `compare.py` in `scorer.py` wiederverwenden; Claims per
  `getattr(claimed, field)` statt eigenem Dict.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

### F-9 – Ringprüfung im Parser und im Modell
- Kategorie: K6
- Ort: `src/carbon_preaudit/calc/inputs.py:101-106, 140-142`, `src/carbon_preaudit/domain/models.py:58-66`
- Schweregrad: niedrig
- Sicherheit: zu prüfen
- Beleg: Geschlossenheit, Mindestlänge 4 und lon/lat-Bereich werden in `_parse_polygon` und erneut im
  Validator von `GeoJSONPolygon` geprüft, mit unterschiedlichen Exception-Typen und Meldungen.
- Auswirkung: Zwei Implementierungen derselben Regel. Review 03 (W3) hat die Prüfung im Modell bewusst
  verlangt, damit Modelle auch ohne Parser gültig bleiben; ob die Doppelung so gewollt ist, ist nicht
  dokumentiert.
- Möglicher Korrekturansatz: Doppelung im Docstring begründen, oder eine gemeinsame Hilfsfunktion nutzen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

### F-10 – Auswahl des Default-Modells doppelt
- Kategorie: K6
- Ort: `evals/runner.py:101-107`, `src/carbon_preaudit/preaudit/extractor.py:140, 201, 249-258`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `requested_model` baut eine eigene Zuordnung `{"gemini": DEFAULT_GEMINI_MODEL, "anthropic":
  DEFAULT_MODEL}` und liest `CARBON_PREAUDIT_MODEL`; die Extractors leiten dasselbe getrennt ab.
- Auswirkung: Ändert sich die Logik im Extractor, kann der Bericht ein anderes Modell als „angefragt“
  ausweisen als tatsächlich angefragt wurde.
- Möglicher Korrekturansatz: Das angefragte Modell vom Extractor erfragen (Attribut), statt es neu abzuleiten.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

### F-11 – Englische Fehlermeldungen in der deutschen Oberfläche
- Kategorie: K6
- Ort: `src/carbon_preaudit/web/app.py:199-200`, Meldungen aus `src/carbon_preaudit/calc/inputs.py`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: Die Oberfläche zeigt `str(e)` aus `InputError`. Meldungen aus `web/app.py` sind deutsch
  („PDD-Text fehlt.“), Meldungen aus `calc/inputs.py` englisch („CSV could not be read: …“, „Line 2: too many
  fields …“).
- Auswirkung: Uneinheitliche Sprache für Nutzer.
- Möglicher Korrekturansatz: Übersetzung in der Oberfläche über den Exception-Typ, oder deutsche Meldungen
  in `calc/`. CLAUDE.md legt Englisch für Bezeichner fest, nicht für Nutzertexte.
- Verhaltensänderung bei Korrektur: ja (Meldungstexte)
- Abhängigkeiten: Tests, die auf Meldungstexte prüfen
- Aufwand: M

## K7 – Halluzinierte oder veraltete APIs und Packages

### F-12 – Laufzeit-Import aus einer Dev-Abhängigkeit
- Kategorie: K7
- Ort: `src/carbon_preaudit/preaudit/extractor.py:8, 225`, `pyproject.toml:31`
- Schweregrad: mittel
- Sicherheit: belegt
- Beleg: `import httpx2` und `except httpx2.HTTPError` im Produktivcode; `httpx2` steht nur unter
  `[dependency-groups] dev`. Installiert ist es zur Laufzeit nur transitiv über `anthropic`/`google-genai`.
- Auswirkung: Ändert eines der SDKs seine HTTP-Bibliothek, schlägt der Import im Image (`--no-dev`) mit
  `ImportError` fehl.
- Möglicher Korrekturansatz: `httpx2` in `[project] dependencies` aufnehmen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: `uv.lock`
- Aufwand: S

### F-13 – Direkter Import einer nicht deklarierten Abhängigkeit
- Kategorie: K7
- Ort: `src/carbon_preaudit/web/highlight.py:10`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `from markupsafe import Markup`; `markupsafe` steht nicht in `pyproject.toml`, es kommt transitiv
  über `jinja2`.
- Auswirkung: Gering, solange `jinja2` von `markupsafe` abhängt.
- Möglicher Korrekturansatz: `markupsafe` deklarieren.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: `uv.lock`
- Aufwand: S

### F-14 – Anthropic-Pfad nie gegen die echte API gelaufen
- Kategorie: K7
- Ort: `src/carbon_preaudit/preaudit/extractor.py:142-173`
- Schweregrad: mittel
- Sicherheit: zu prüfen
- Beleg: Der Aufruf nutzt `beta.messages.create` mit `betas=["server-side-fallback-2026-07-01"]`,
  `fallbacks="default"` und `output_config.format` (JSON-Schema). Die Parameter sind laut Review 05 gegen
  die SDK-Signatur 2.3.0 geprüft; ein Lauf gegen die API ist weder in Tests noch in den Evals belegt
  (Evals liefen mit Gemini).
- Auswirkung: Ob die API die Kombination akzeptiert, ist offen. Fällt der Anbieter auf `anthropic`, könnte
  jeder Aufruf mit 400 scheitern.
- Möglicher Korrekturansatz: Einen Eval-Lauf mit `CARBON_PREAUDIT_PROVIDER=anthropic` durchführen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: braucht `ANTHROPIC_API_KEY`
- Aufwand: S

## K8 – Unbelegte Erfolgsbehauptungen

### F-15 – Commit-Angabe im Eval-Bericht passt nicht zum Lauf
- Kategorie: K8
- Ort: `evals/results/latest.md:3, 11`
- Schweregrad: mittel
- Sicherheit: belegt
- Beleg: Der Bericht nennt `Zeitpunkt (UTC): 2026-10-31 12:04:56` und `Git-Commit: a057e3c`. Commit
  `a057e3c` entstand um 12:07:41 UTC (`git log -1 --format=%ci a057e3c`), also nach dem Lauf. Der Lauf
  um 12:04:56 lief auf `1e24220-dirty`; die Commit-Zeile wurde nachträglich geändert.
- Auswirkung: Der Bericht weist eine Herkunft aus, auf der er nicht entstanden ist. Der Prompt-Hash
  (`3ebd19b1d751`) entspricht dem Prompt in `a057e3c`.
- Möglicher Korrekturansatz: (a) Eval-Lauf auf dem aktuellen Stand wiederholen und Bericht ersetzen.
  (b) Commit-Zeile auf den tatsächlichen Stand zurücksetzen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: (a) braucht `GEMINI_API_KEY`
- Aufwand: S

### F-16 – Strukturangaben in CLAUDE.md veraltet
- Kategorie: K8
- Ort: `CLAUDE.md:124-125`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `preaudit/ # extractor.py (Protocol + Anthropic + Fake)` nennt den Gemini-Extractor (Default) nicht;
  `store/ # Persistenz der Läufe` existiert nicht (Schritt 04 zurückgestellt).
- Auswirkung: Agenten und Leser erhalten ein unzutreffendes Bild der Struktur.
- Möglicher Korrekturansatz: Zeilen an den Stand anpassen, `store/` als geplant markieren.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

### F-32 – Container-Start laut README ohne API-Key
- Kategorie: K8
- Ort: `README.md` (Abschnitt „Im Container starten“), `.dockerignore`
- Schweregrad: mittel
- Sicherheit: belegt
- Beleg: Der dokumentierte Befehl `podman run … carbon-preaudit` übergibt keine Umgebungsvariablen; `.env`
  ist per `.dockerignore` nicht im Image. Im Container fehlt damit jeder Key, `POST /check` zeigt immer
  „Extraktion fehlgeschlagen“. Entdeckt bei der Korrektur von F-21.
- Auswirkung: Die Prüfung, der Kern der Demo, funktioniert im Container nach README nicht; Kennzahlen und
  Karte erscheinen trotzdem.
- Möglicher Korrekturansatz: (a) `--env-file .env` im README-Befehl. (b) Hinweis, dass der Container ohne Key
  nur rechnet.
- Verhaltensänderung bei Korrektur: nein (Code), ja (dokumentierter Ablauf)
- Abhängigkeiten: F-21
- Aufwand: S

## K9 – Unvollständige Implementierungen

### F-17 – README-Abschnitt „Bewusst nicht enthalten“ fehlt
- Kategorie: K9
- Ort: `README.md`; Verweise in `CLAUDE.md:52` und `docs/plans/01-architecture.md:286`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: CLAUDE.md: „Diese Punkte landen nur im README-Abschnitt ‚Bewusst nicht enthalten‘.“ Plan:
  „Kommt nach ‚Bewusst nicht enthalten‘.“ Die README hat keinen solchen Abschnitt (`grep -n "^#" README.md`).
- Auswirkung: Die dokumentierte Abgrenzung des Scopes ist für Leser des Repos nicht auffindbar.
- Möglicher Korrekturansatz: Abschnitt anlegen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

## K10 – Spuren von Kontextverlust

### F-18 – Widersprüchliche Regel zur Erhöhung von `CALC_VERSION`
- Kategorie: K10
- Ort: `CLAUDE.md` (Code-Konventionen), `src/carbon_preaudit/calc/version.py:1`,
  `docs/adr/0002-reproducible-runs-via-hash.md:45`, Commit `6badffb`
- Schweregrad: niedrig
- Sicherheit: zu prüfen
- Beleg: CLAUDE.md und `version.py`: „Jede Logikänderung in `calc/` erhöht `CALC_VERSION`.“ ADR 0002: „Ein
  Refactoring ohne Ergebnisänderung braucht keine neue `CALC_VERSION`.“ Commit `6badffb` ändert Logik in
  `calc/inputs.py` ohne Erhöhung, mit Verweis auf ADR 0002.
- Auswirkung: Zwei Quellen geben unterschiedliche Regeln; welche gilt, hängt davon ab, wer liest.
- Möglicher Korrekturansatz: Eine Formulierung in beiden Quellen, z. B. „jede Änderung, die Ergebnisse
  ändert“.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

## K11 – Security, Performance, Edge Cases

### F-19 – Fehler aus der Rechnung führen in `/check` zu HTTP 500
- Kategorie: K11
- Ort: `src/carbon_preaudit/web/app.py:191-201`
- Schweregrad: hoch
- Sicherheit: belegt
- Beleg: `calculate(inputs)` steht nach dem `try/except InputError`. `calculate` wirft `InvalidValueError`
  (Überlauf, `run.py:28-31, 43-44`) und über `polygon_area_ha` `InvalidGeometryError` (Loch nicht kleiner als
  Außenring, `area.py:26-30`), beide Unterklassen von `InputError`. Nachgestellt mit TestClient und
  `FakeExtractor`: Polygon mit Loch größer als Außenring → 500; CSV mit `dbh_cm=1e300, height_m=1e300` → 500.
- Auswirkung: Ungültige Eingaben erzeugen einen Serverfehler statt einer lesbaren Meldung; HTMX zeigt bei
  500 nichts an.
- Möglicher Korrekturansatz: `calculate` in den `try`-Block aufnehmen.
- Verhaltensänderung bei Korrektur: ja (422 mit Meldung statt 500)
- Abhängigkeiten: keine
- Aufwand: S

### F-20 – Mehrdeutige Zahlenlesart lässt Fehllesung als belegt durch
- Kategorie: K11
- Ort: `src/carbon_preaudit/preaudit/compare.py:64-84, 143-146`
- Schweregrad: hoch
- Sicherheit: belegt
- Beleg: `_readings("8.364")` liefert `{8.364, 8364.0}`. Liest das LLM in einem deutsch formatierten Text
  8.364 statt 8364, besteht der Wert die Prüfung „Wert im Zitat“ und wird gegen 8 363,7 verglichen. Erster
  Eval-Lauf am 2026-10-31: Fall `clean-03` ergab zwei falsche `critical`-Befunde (behauptet 8,4 bzw. 6,7
  tCO₂e). Behoben wurde das im Prompt, nicht in `compare.py`.
- Auswirkung: Ein Lesefehler des LLM wird als kritische Abweichung mit Zitat ausgegeben. Die Absicherung
  hängt allein am Prompt; die deterministische Prüfung fängt diesen Fall nicht ab.
- Möglicher Korrekturansatz: (a) Zahlenformat des gesamten Texts bestimmen und nur diese Lesart zulassen.
  (b) Bei mehrdeutigem Zitat und Abweichung einen `info`-Befund statt `critical`. (c) Verhalten belassen und
  dokumentieren.
- Verhaltensänderung bei Korrektur: ja (bei (a)/(b))
- Abhängigkeiten: Eval-Fall `clean-03`, Tests in `tests/test_compare.py` zur Mehrdeutigkeit
- Aufwand: M

### F-21 – `/check` ohne Zugriffsschutz und Begrenzung, jeder Aufruf kostet LLM-Tokens
- Kategorie: K11
- Ort: `src/carbon_preaudit/web/app.py:175-223`, `Dockerfile:25-27`
- Schweregrad: mittel
- Sicherheit: zu prüfen
- Beleg: Jeder `POST /check` mit gültigen Eingaben löst einen LLM-Aufruf mit dem Key des Betreibers aus,
  bis zu 20 000 Zeichen Text. Kein Login, keine Ratenbegrenzung. Der Container lauscht auf `0.0.0.0:8000`.
- Auswirkung: Wird der Container erreichbar betrieben, kann jeder Kosten und Quota-Verbrauch auslösen.
  Lokal ohne Port-Freigabe ohne Auswirkung. Mandanten und Login sind laut CLAUDE.md nicht im Scope.
- Möglicher Korrekturansatz: Betrieb nur lokal dokumentieren; oder einfache Ratenbegrenzung bzw.
  Token-Schutz.
- Verhaltensänderung bei Korrektur: ja (bei Begrenzung)
- Abhängigkeiten: keine
- Aufwand: S (Doku), M (Begrenzung)

### F-22 – Neuer LLM-Client pro Anfrage
- Kategorie: K11
- Ort: `src/carbon_preaudit/web/app.py:74-84`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `_LazyExtractor.extract` ruft bei jedem Aufruf `make_extractor()` auf; der Gemini- bzw.
  Anthropic-Client wird jedes Mal neu erzeugt.
- Auswirkung: Kein Wiederverwenden von Verbindungen; zusätzlicher Aufbau pro Anfrage.
- Möglicher Korrekturansatz: Extractor einmal beim ersten Aufruf erzeugen und cachen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

### F-23 – Mehrfache Git-Aufrufe in der Versionsprüfung
- Kategorie: K11
- Ort: `tools/local_tools/bump_script.py:87-88`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `is_version_valid` ruft `_latest_tag_version()` viermal auf (dreimal über `_generate_version`,
  einmal direkt), jedes Mal mit Git-Aufrufen durch dunamai. Review 05 nannte für die Bump-Tests rund 26 s.
- Auswirkung: Langsame Tests und CI-Schritte. `pytest --durations` am 2026-10-31: die fünf langsamsten Tests
  sind alle in `tests/test_bump_script.py` (bis 3,4 s je Test).
- Möglicher Korrekturansatz: Tag-Version einmal bestimmen und weiterreichen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: keine
- Aufwand: S

## K12 – Unnötige Dependencies und Kommentar-Rauschen

### F-24 – `sqlalchemy` deklariert, aber nicht verwendet
- Kategorie: K12
- Ort: `pyproject.toml:14`
- Schweregrad: niedrig
- Sicherheit: belegt
- Beleg: `sqlalchemy>=2.1.6` in `[project] dependencies`; kein Import in `src`, `evals`, `tools`, `tests`.
  Vorgesehen für Schritt 04, der zurückgestellt ist.
- Auswirkung: Zusätzliches Paket im Docker-Image und in der Angriffsfläche ohne Nutzung.
- Möglicher Korrekturansatz: Entfernen bis Schritt 04, oder als geplant belassen.
- Verhaltensänderung bei Korrektur: nein
- Abhängigkeiten: `uv.lock`
- Aufwand: S

## Bewusst nicht als Finding gewertet

- `vulture` (21 Treffer, 60 %): Pydantic-Felder und Validatoren, FastAPI-Routen und Click-Befehle per
  Decorator, `FakeExtractor` (in Tests genutzt). Alle sind Framework-Nutzung, kein toter Code.
- `src/carbon_preaudit/calc/area.py:17`, `src/carbon_preaudit/preaudit/extractor.py:206`,
  `src/carbon_preaudit/web/app.py:60-61` – `pyright: ignore[reportUnknownMemberType]`: unbekannte Typen in
  pyproj, google-genai bzw. Jinja2, jeweils kommentiert.
- `tests/test_inputs.py:245, 256, 260`, `tests/test_preaudit_models.py:33` – Ignore-Kommentare in Tests, die
  absichtlich ungültige Werte übergeben.
- `evals/runner.py:89` – `except OSError, subprocess.CalledProcessError:` ist ab Python 3.14 gültige Syntax.
- `assert … is not None` in Tests (`tests/test_evidence_span.py:12, 27`, `tests/test_extractor.py:340, 472`,
  `tests/test_evals_runner.py:64`, `tests/test_compare.py:271, 289`): jeweils Typ-Einengung, gefolgt von
  Wertprüfungen.
- `src/carbon_preaudit/calc/inputs.py:196` – `row.get("wood_density")`: Spalte ist laut Scope optional.
- `src/carbon_preaudit/web/app.py:166-170` – Exception-Handler für 400 auf `/check`: begrenzt auf genau
  diesen Fall, sonst Standardverhalten.
- Secrets: `git grep` auf Anthropic-, Google- und GitHub-Schlüsselmuster sowie PEM-Blöcke in Dateien und
  Historie ohne Treffer.

## Nicht geprüft

- Abhängigkeiten auf bekannte Sicherheitslücken: kein `pip-audit`/`osv-scanner` vorhanden; Dependabot-Alerts
  auf GitHub wurden nicht abgefragt.
- Secret-Scan mit Spezialwerkzeug: nicht vorhanden, nur manuelle Muster.
- Duplikat-Erkennung mit Werkzeug: nicht vorhanden, nur Lesen.
- `release.yml`: nie ausgeführt, nur gelesen.
- Frontend (`web/static/app.js`, `style.css`): gelesen, nicht im Browser auf Edge Cases getestet.
- Anthropic-Extractor gegen die echte API (siehe F-14).
- Existenz der Pakete in der Registry: nicht abgefragt; alle Pakete sind installiert und importierbar
  (Testlauf grün), daher kein Verdacht auf erfundene Pakete.
