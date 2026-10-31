# Review 06: Evals

Geprüft: uncommittete Änderungen auf `feat/06-evals` (`evals/__init__.py`, `evals/__main__.py`,
`evals/cases.py`, `evals/runner.py`, `evals/scorer.py`, `evals/report.py`, `evals/cases/*.yaml`,
`tests/test_evals_cases.py`, `tests/test_evals_runner.py`, `tests/test_evals_scorer.py`,
`src/carbon_preaudit/preaudit/extractor.py`, `tests/test_extractor.py`, `pyproject.toml`,
`docs/plans/01-architecture.md`) ·
Grundlage: `docs/plans/01-architecture.md` (Abschnitt „06 Evals“, „Offene Fragen“), `CLAUDE.md`,
ADR 0001, ADR 0002, ADR 0006 (App-Version), ADR 0008

Selbst ausgeführt: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` (0 Fehler)
und `uv run pytest` (274 grün). Für alle 12 Fälle lief ein Skript mit perfekter Extraktion: Wert und Zitat
(ganzer Satz bzw. Aufzählungspunkt) direkt aus dem Falltext, `compare()` gegen `calculate_examples()`,
danach `match_case()`. Kein Netzwerk. Den Gemini-Client habe ich mit Dummy-Key gebaut und die wirksamen
Retry- und Timeout-Werte ausgelesen. `.env` habe ich nicht gelesen, und einen echten Eval-Lauf habe ich nicht gestartet.

Ohne Befund geprüft:
- Lauf über `examples/`: 100,0186 ha, 8.363,695 tCO₂e brutto, 6.690,956 tCO₂e netto, Puffer 20 %.
  Handrechnung tC-Fall: 8.363,695 / (44/12) = 2.280,99, damit liegt 2.281 tC im 2-%-Fenster. Netto
  8.364 gegen 6.690,956 ergibt +25,0 %, das ist außerhalb, und gegen brutto 8.363,695 ergibt +0,004 %,
  also „brutto/netto verwechselt“.
- Alle 12 Fälle liefern bei perfekter Extraktion **genau** den erwarteten Befund samt Diagnose. Die
  fehlerfreien Fälle liefern keinen. Alle Zitate haben mindestens 3 Wörter, liegen an Wortgrenzen und
  enthalten den Wert. Das deutsche Format in `clean-03` („100,0 ha“, „8.364 tCO2e“) wird über
  `number_candidates` richtig gelesen. Die Fälle messen damit die Extraktion und keine Fehler in den Fällen
  selbst.
- Verteilung laut Plan: 3 fehlerfrei, 3 Fläche, 2 Tonnen (je eine Diagnose), 2 Puffer, 2 fehlend.
- `match_case` ist 1:1. Gematcht wird auf Gleichheit von (`field`, `severity`), also auf
  Äquivalenzklassen, deshalb ist die gierige Zuordnung optimal für TP/FP/FN. Ein falscher Schweregrad
  zählt als FP+FN (`field_counts`, Test `test_wrong_severity_counts_as_fp_and_fn`). Bei 0/0 liefern
  Precision und Recall `None`, im Bericht steht dann „–“. „Gesamt“ ist die Summe über die Felder.
- Diagnosen werden getrennt gezählt. `expected` enthält auch verfehlte Erwartungen, und `unexpected`
  zählt falsche Diagnosen auf Treffern plus Diagnosen auf Extras.
- `run_cases` fängt `ExtractionError` je Fall ab, der Fall wird nicht bewertet und als Fehler gelistet.
  `extracted_by` wird aus `ClaimedValues` übernommen. Fall-Reihenfolge (sortiert nach Dateiname), Feld-
  und Modell-Reihenfolge sind deterministisch. Bis auf den Zeitstempel ist der Bericht bei gleichen
  Befunden gleich. `run_hash`, `PARAMS_VERSION`, `CALC_VERSION`, App-Version und Modell stehen im Kopf.
- `HttpRetryOptions` passt zum installierten SDK (google-genai 2.34.0, `_api_client.py:667-699`):
  `attempts=4` sind 4 Versuche insgesamt, die Statusliste ersetzt die Default-Liste (408 fällt also weg),
  und gewartet wird per `wait_exponential_jitter`. Geprüft am gebauten Client: `stop_after_attempt`,
  `initial=1.0`, `max=30.0`, `exp_base=2.0`, `jitter=1`.
- `evals` ist in pyright `include` und `strict`, `pythonpath = ["."]` ist gesetzt, `scorer.py` macht kein
  I/O, und nichts geht über 06 hinaus. In den Tests kommen nur `FakeExtractor` bzw. Stubs vor.

## Kritisch

Keine.

## Wichtig

- [x] **W1** `docs/plans/01-architecture.md:294-297`, `evals/runner.py:109`, `evals/report.py:67`: Der Plan
  sagt, für `compare()` gebe es keine eigene Version, weil „die App-Version das abdeckt“. Das stimmt nicht.
  `version("carbon-preaudit")` liest die statische Version aus `pyproject.toml` (aktuell `0.1.0`, `git
  describe` ergibt `0.0.0-6-g1e24220-dirty`), und die ändert nur das Bump-Skript vor einem Release (ADR 0006).
  Änderungen an `compare.py`, `SYSTEM_PROMPT`, den Toleranzen in `compare` oder an den Fällen zwischen zwei
  Releases bleiben im Bericht unsichtbar. Zwei Berichte mit gleicher App-Version können also von
  verschiedenem Code stammen. Gerade bei Evals ist der Prompt die wichtigste Variable.
  Vorschlag: Commit und Dirty-Flag in den Bericht schreiben (`git describe --always --dirty` oder dunamai,
  das ohnehin im Projekt ist), dazu einen kurzen Hash über `SYSTEM_PROMPT`. Den Satz im Plan danach anpassen.
  Erledigt: Bericht enthält Git-Commit (kurz, `-dirty`, ohne Git „–“; Abfrage in `runner.git_revision`) und Prompt-Hash (SHA-256, 12 Zeichen); Plansatz korrigiert.
- [x] **W2** `src/carbon_preaudit/preaudit/extractor.py:169-180`: Ein Timeout ist nicht gesetzt, weder pro
  Versuch noch gesamt. `HttpOptions.timeout` bleibt `None`, das SDK setzt dann `timeout=None` am
  httpx2-Client (`_api_client.py:1414-1415`). Am gebauten Client geprüft: `Timeout(timeout=None)`. Ein
  hängender Request blockiert den Eval-Lauf (und später `POST /check`) unbegrenzt, und Retry greift nie,
  weil nie ein `TimeoutException` entsteht. Die Backoff-Wartezeit ist dagegen klein: 3 Pausen von etwa
  1, 2 und 4 s plus je bis zu 1 s Jitter, zusammen höchstens etwa 10 s. `max_delay=30.0` wird mit 4 Versuchen
  nie erreicht.
  Vorschlag: `HttpOptions(timeout=...)` setzen (Einheit **Millisekunden**, `types.py:2737`), etwa 60 000 ms
  pro Versuch. Im Worst Case dauert ein Fall dann rund 4 × 60 s + 10 s. Als Konstante neben
  `GEMINI_RETRY_ATTEMPTS` ablegen und im Test `test_gemini_client_is_built_with_retry_options` prüfen.
  Erledigt: `HttpOptions(timeout=60_000)` (Millisekunden, per Versuch), Backoff 2/4/8 s + je bis 1 s Jitter, `max_delay=10`; höchstens 17 s Wartezeit, Worst Case je Aufruf 257 s (Kommentar am Code); Test prüft alle Werte.
- [x] **W3** `tests/test_evals_cases.py` (fehlt): Kein Test prüft, dass die 12 echten Fälle bei perfekter
  Extraktion genau ihre `expected`-Befunde liefern. Heute stimmt das (siehe oben), aber nur zufällig
  abgesichert. Ändern sich Toleranzen, `PARAMS_VERSION`, `examples/plots.csv` oder die Zitatregeln in
  `compare.py`, werden Fälle still falsch. Die Evals messen dann Fehler in den Fällen und nicht in der
  Extraktion, und genau das sollen sie nicht. Der Test „`uv run python -m evals` läuft durch“ fängt das
  nicht ab.
  Vorschlag: ein parametrisierter Unit-Test je Fall mit einem `FakeExtractor` und den von Hand gesetzten
  `ClaimedValues` (Wert + wörtliches Zitat), der `match_case(...).passed` und die Diagnosen prüft. Die
  Sollwerte gehören in den Test, nicht in die YAML, damit das Fallformat gleich bleibt.
  Erledigt: `tests/test_evals_cases_consistency.py` prüft je Fall mit perfekter Extraktion (Werte und ganze Sätze aus dem Text) exakt `expected` inklusive Diagnose.

## Hinweis

- [x] **H1** `src/carbon_preaudit/preaudit/extractor.py:24`: Der Kommentar „only 429 and 5xx“ ist ungenau.
  Das SDK wiederholt unabhängig von `http_status_codes` auch `httpx2.TimeoutException` und `ConnectError`
  (`_api_client.py:96-101`, `683-686`). Das ist gewollt, sobald W2 ein Timeout setzt, gehört aber in den
  Kommentar.
  Erledigt: Kommentar nennt jetzt auch `TimeoutException` und `ConnectError` sowie die Einheiten.
- [x] **H2** `evals/report.py:39-43`: Der Fallback für das Modell nimmt nur `CARBON_PREAUDIT_MODEL`. Schlagen
  alle Fälle fehl und ist die Variable nicht gesetzt, steht „–“ im Bericht, obwohl das Default-Modell des
  Anbieters (`DEFAULT_GEMINI_MODEL` bzw. `DEFAULT_MODEL`) feststeht. Außerdem werden „angefragt“ (env) und
  „hat geantwortet“ (`extracted_by`) nicht unterschieden. Durch das Lesen von `os.environ` ist
  `render_report` auch nicht mehr rein. Vorschlag: das angefragte Modell als Parameter übergeben, wie
  `provider`.
  Erledigt: `render_report` bekommt `model`, `git_commit`, `prompt_hash` als Argumente und liest keine Umgebung mehr; Bericht zeigt „Modell (angefragt)“ (Override oder Anbieter-Default) und „Modell (geantwortet)“ getrennt.
- [x] **H3** `evals/report.py:55-56`, `69`: Fälle mit Extraktionsfehler fehlen in den Metriken. Ihre
  erwarteten Befunde zählen also nicht als FN, und der Recall wirkt besser, als er ist. Der Bericht nennt
  zwar die Fehlerzahl, sagt aber nicht, dass die Tabelle nur über N bewertete Fälle geht. Vorschlag: eine
  Zeile „Bewertet: N von M Fällen“ über der Tabelle.
  Erledigt: Zeile „Bewertet: N von M Fällen“ mit ausdrücklichem Hinweis, dass Fälle mit Extraktionsfehler nicht in den Metriken stehen.
- [x] **H4** `evals/runner.py:116`: `main` gibt auch dann 0 zurück, wenn jede Extraktion fehlschlug. Für
  „läuft durch“ reicht das, ein Skript oder eine spätere CI erkennt den Totalausfall aber nicht. Vorschlag:
  ein eigener Exit-Code (etwa 1), wenn kein Fall bewertet wurde.
  Erledigt: Exit 1, wenn mindestens ein Fall einen Extraktionsfehler hatte, sonst 0; Metriken lösen keinen Exit 1 aus.
- [x] **H5** `tests/test_evals_scorer.py`: Zwei Zweige von `diagnosis_score` sind ungetestet: eine
  verfehlte Erwartung mit Diagnose zählt in `expected` (`scorer.py:100`), und ein Extra mit Diagnose zählt
  in `unexpected` (`scorer.py:107`). Beides ist ein Einzeiler mit festen Befundlisten.
  Erledigt: zwei neue Tests in `tests/test_evals_scorer.py` für die Zweige verfehlte Erwartung mit Diagnose und Extra mit Diagnose.
- [x] **H6** `evals/scorer.py:73-81`: Bei mehreren Befunden mit gleichem (`field`, `severity`) und
  verschiedenen Diagnosen kann die gierige Zuordnung über Kreuz paaren und Diagnosen als falsch zählen,
  obwohl eine passende Paarung existiert. Mit `compare()` passiert das nicht, weil es höchstens einen Befund
  je Feld liefert. Vorschlag: im Docstring festhalten oder bei gleichem Paar zuerst nach passender Diagnose
  suchen.
  Erledigt: dokumentiert (Docstring von `match_case`).
- [x] **H7** `evals/results/`: Es gibt noch keinen Bericht `latest.md`. Der DoD-Punkt
  „`uv run python -m evals` läuft durch“ ist also nur mit Fakes belegt. Den echten Lauf muss der Mensch mit
  Key starten. Danach den Plan-Fortschritt für 06 abhaken.
  Erledigt: Echter Lauf mit gemini-3.5-flash-lite, 12 von 12 Fällen bewertet, Precision und Recall 100 %.
  Davor hat ein erster Lauf 4 Fehlalarme gezeigt (zu kurze Zitate, deutsches Zahlenformat), behoben im Prompt.

## Fazit

Kritische Befunde gibt es nicht. Scorer, Runner und Fälle sind fachlich richtig, und mit perfekter
Extraktion liefert jeder Fall genau den erwarteten Befund. Abnahmefähig ist der Schritt nach W1
(Code-Stand und Prompt im Bericht, Plansatz korrigieren), W2 (Timeout) und W3 (Test, der die Fälle gegen
`compare()` absichert), dazu ein echter Lauf durch den Menschen (H7).
