# Review 05: Pre-Audit

Geprüft: uncommittete Änderungen auf `feat/05-preaudit` (`src/carbon_preaudit/preaudit/*`,
`src/carbon_preaudit/domain/models.py`, `src/carbon_preaudit/calc/params.py`, `examples/pdd-section.md`,
`tests/test_compare.py`, `tests/test_extractor.py`, `tests/test_preaudit_models.py`,
`tests/test_calc_golden.py`, `docs/plans/01-architecture.md`, `CLAUDE.md`) ·
Grundlage: `docs/plans/01-architecture.md` (Pre-Audit, Domänenmodelle, DoD „05 Pre-Audit“), `CLAUDE.md`,
ADR 0001, ADR 0002, Entscheidungen des Menschen (Default-Modell `claude-opus-5-5` über
`CARBON_PREAUDIT_MODEL`, Wertprüfung mit `info`-Befund „Wert nicht im Zitat belegt“)

Selbst ausgeführt: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` (0 Fehler)
und `uv run pytest` (193 grün). Die Randfälle unten habe ich mit Skripten gegen `_number_candidates`,
`compare` und `AnthropicExtractor` geprüft. Für den Extractor lief ein `anthropic.Anthropic` mit
`httpx2.MockTransport`, also ohne Netzwerk. Die Ergebnisse stehen jeweils beim Befund.

Ohne Befund geprüft:
- Regeltabelle, `≤` an allen Grenzen, Schweregrade und Reihenfolge der Diagnosen entsprechen dem Plan.
- `tc_instead_of_tco2e` wird vor `gross_net_swapped` geprüft. Beide gleichzeitig können nicht passen,
  weil wegen `k_net ≤ k_gross` gilt `k_net / (44/12) < k_gross / 3,6`, und die 2-%-Fenster überlappen
  nicht.
- `tco2e_net` in tC wird gegen `k_net / (44/12)` geprüft (`compare.py:167`, `k` ist der Wert des
  eigenen Felds), getestet in `test_diagnosis_tc_on_net`.
- `client.beta.messages.parse` ist gegen SDK 2.3.0 richtig verwendet. `output_format` wird in
  `output_config.format` eingefügt, `effort` bleibt erhalten, und der Beta-Header wird gesetzt
  (geprüft am Request-Body).
- `MAX_TOKENS = 8000` reicht für etwa 500 Ausgabe-Tokens plus Thinking bei `effort: low`, und es bleibt
  unter der Grenze für Requests ohne Streaming.
- `compare.py` ist ohne I/O und ohne `Any`, und das Ergebnis hängt nicht von der Reihenfolge der
  Kandidaten im `set` ab.
- Nichts aus 06 oder 07 ist enthalten, und kein Test geht über das Netzwerk.

Handrechnung (`test_example_pdd_section_with_tc_instead_of_tco2e`): k_gross = 8363,695 tCO₂e,
k_gross / (44/12) = 8363,695 · 12/44 = 2281,008 tC. Behauptet sind 2279. Damit ist
|2279 − 2281,008| / 2281,008 = 0,00088 ≤ 0,02, die tC-Diagnose greift also. Die Abweichung zu k ist
2279 / 8363,695 − 1 = −72,75 %, also `critical`. Das stimmt mit dem Test überein. Beispieltext:
8364 gegen 8363,695 ergibt +0,0036 %, 6691 gegen 6690,956 ergibt +0,0007 %, 100,0 ha gegen 100,019 ha
ergibt −0,019 %. Alle drei liegen in der Toleranz, und `compare` liefert `[]`.

## Kritisch

- [x] **K1** `tests/test_calc_golden.py:52`, `src/carbon_preaudit/calc/params.py:16`: Der bestehende
  Eintrag `PARAMS_GOLDEN["1"]` wurde um `QUOTE_VALUE_REL_TOL` erweitert, ohne dass `PARAMS_VERSION`
  steigt. ADR 0002 schreibt vor: „Bestehende Einträge in `GOLDEN` und `PARAMS_GOLDEN` werden nie
  geändert, Reviews lehnen solche Änderungen ab. Neue Werte bekommen eine neue Version.“ Version `"1"`
  ist mit #6 schon auf `master`. Fachlich ändert sich an der Berechnung nichts, weil die neue Konstante
  nicht in `calc/` vorkommt. Trotzdem bedeutet `PARAMS_VERSION = "1"` jetzt zwei verschiedene
  Parametersätze, und genau diese Mehrdeutigkeit soll die Regel verhindern. Vorschlag, der Mensch
  entscheidet:
  (a) `PARAMS_VERSION = "2"` und dazu ein neuer Eintrag `PARAMS_GOLDEN["2"]`. Dann ändert sich der
  `run_hash` im Golden-Fall. Der Eintrag `GOLDEN["1"]["run_hash"]` hängt also auch an
  `PARAMS_VERSION`, und `GOLDEN` braucht einen Schlüssel aus beiden Versionen.
  (b) ADR 0002 ergänzen: Eine neue Konstante, die keinen Rechenwert ändert, darf in die laufende
  Version aufgenommen werden. Dann ist die Änderung keine Ausnahme ohne Beschluss.

  Erledigt: `QUOTE_VALUE_REL_TOL` aus `params.py` entfernt, jetzt Modulkonstante `_QUOTE_VALUE_REL_TOL` in `compare.py` (technische Float-Gleichheit, kein Fachwert). `PARAMS_GOLDEN["1"]` entspricht wieder master (`git diff master -- tests/test_calc_golden.py` leer), Plan-Parametertabelle angepasst.

## Wichtig

- [x] **W1** `src/carbon_preaudit/preaudit/compare.py:39`, `:84`: Für eine Folge von Ziffergruppen, die
  durch Leerzeichen getrennt sind, gelten nur die ganze Verschmelzung und jede einzelne Gruppe als
  Kandidat. Damit kommt es zu Fehlern in beide Richtungen:
  - Falsch belegt: Bei „20 100 ha“ zählen 20, 100 und 20100. Liest das Modell 100 statt 20 100, wird
    der Wert als belegt verglichen. Gegen k = 100 ha entsteht dann kein Befund, obwohl der Text
    20 100 ha behauptet. Ebenso gelten 8 und 364 aus „8 364“ als belegt.
  - Falsch nicht belegt: Bei „year 2023 8 364“ sind die Kandidaten {2023, 8, 364, 20238364}. Die
    richtige Zahl 8364 fehlt, also entsteht nur `info` „Wert nicht im Zitat belegt“. Eine echte
    Tonnen-Abweichung (`critical`) geht so verloren.
  - `\s` umfasst auch `\n` und `\t`, deshalb werden Zahlen über Zeilenumbrüche hinweg verschmolzen. Der
    Plan nennt als Trenner nur Leerzeichen und schmales Leerzeichen.

  Vorschlag: Als Trenner nur ` `, U+00A0 und U+202F zulassen. Kandidaten sind alle zusammenhängenden
  Teilfolgen, deren Folgegruppen genau 3 Ziffern haben (also gültige Tausendergruppen). Ob eine Gruppe
  einzeln zählt, wenn sie Teil einer gültigen Tausendergruppierung ist, sollte bewusst entschieden und im
  Plan unter „Wertprüfung“ festgehalten werden. Tests für „20 100“ und „2023 8 364“ ergänzen.

  Erledigt: `number_candidates` gruppiert Tausender gierig von links (erste Gruppe 1–3 Ziffern, weitere genau 3, Trenner nur Leerzeichen, NBSP, schmales Leerzeichen); Einzelgruppen einer gültigen Zahl sind keine Kandidaten. Tests für „20 100“, „year 2023 8 364“, Zeilenumbruch, Doppelleerzeichen; Plan unter „Wertprüfung“ ergänzt.

- [x] **W2** `src/carbon_preaudit/preaudit/extractor.py:24-25`, `:36-38`: Laut Feldbeschreibung sind
  `tco2e_gross` und `tco2e_net` Werte „in tCO2e“. Nur die Regel in Zeile 30-31 sagt, dass ein tC-Wert ein
  tC-Wert bleibt. Bei „The gross removals amount to 2,279 tC“ kann das Modell deshalb zu Recht
  schließen, dass das Feld in tCO₂e nicht vorkommt, und `null` liefern. Dann kommt `info` „im Text nicht
  gefunden“ statt `critical` mit `tc_instead_of_tco2e`, und die Diagnose greift nie. ADR 0001 sagt
  ausdrücklich, dass die tC-Diagnose nur funktioniert, wenn der Prompt das sicherstellt. Vorschlag:
  Feldbeschreibung neutral fassen, etwa „the total removals before any buffer deduction, as a number in
  the unit stated in the text (tCO2e or tC)“, und die tC-Regel daneben stellen. Den Eval-Fall dafür
  in 06 fest einplanen.

  Erledigt: Feldbeschreibung der Tonnen einheitenneutral („in the unit stated in the text (tCO2e or tC), never converted“), Regel ergänzt, dass eine tC-Angabe extrahiert und nicht auf null gesetzt wird. Prompt-Test ergänzt. Der Eval-Fall dafür gehört weiterhin in 06.

- [x] **W3** `src/carbon_preaudit/preaudit/extractor.py:116-125`, `tests/test_extractor.py:125-134`:
  Das SDK parst den Text schon im `post_parser` von `parse()` mit `TypeAdapter.validate_json`, also
  bevor `stop_reason` ausgewertet wird. Mit Mock-Transport nachgestellt:
  - `refusal` mit Textblock („I can't help with that.“) ergibt `ExtractionError("Model output does not
    match the schema: … Invalid JSON …")`, nicht „refused“.
  - `max_tokens` mit abgeschnittenem JSON ergibt dieselbe Schema-Meldung, ohne `stop_reason`.
  - `max_tokens` mit gültigem, vollständigem JSON wird angenommen.

  Der Zweig `refusal` in Zeile 120 wird nur erreicht, wenn der Inhalt leer ist. Der Test
  `test_refusal_raises_extraction_error` gibt bei `refusal` eine geparste Ausgabe zurück, also einen
  Zustand, den das echte SDK so nicht liefert. Der Test belegt das Verhalten deshalb nicht. Ein
  `ExtractionError` entsteht zwar immer, aber die Ursache steht für Evals und UI falsch drin.
  Vorschlag: `client.beta.messages.create` mit `output_config.format` aufrufen und selbst parsen, oder
  `ValidationError` abfangen und die Meldung neutral fassen. Dann zuerst `stop_reason` prüfen
  (`refusal`, `max_tokens`) und erst danach `ExtractionOutput.model_validate_json`. Den Fake im Test so
  bauen, dass er das SDK-Verhalten abbildet.

  Erledigt: `client.beta.messages.create` mit `output_config` (`format` aus `anthropic.transform_schema(ExtractionOutput)`, `effort: low`); `stop_reason` (`refusal`, `max_tokens`) wird vor `ExtractionOutput.model_validate_json` geprüft. Test-Fakes liefern echte `BetaMessage`-Objekte (Tests: Refusal mit Text, abgeschnittenes JSON, ungültiges JSON, Thinking-Block).

- [x] **W4** `src/carbon_preaudit/preaudit/compare.py:202`, `:204`: Die Zitatprüfung ist eine reine
  Teilstring-Prüfung ohne Wortgrenzen und ohne Mindestinhalt. Geprüft:
  - Behauptet sind `tco2e_gross = 20` mit Zitat „20“ bei Text „A share of 20 % …“. Das ergibt
    `critical` „behauptet 20,0 tCO₂e, berechnet 8.363,7 tCO₂e“. Dieser kritische Befund wirkt belegt,
    aber das Zitat zeigt nicht, dass 20 die Brutto-Menge ist.
  - Das Zitat „0 ha“ ist Teilstring von „100.0 ha“, und 0 steht als Wert darin. Das ergibt einen
    `major`-Befund mit einem Zitat, das so im Text nicht als Wort steht.

  Leitprinzip 3 ist damit formal erfüllt, weil das Zitat wörtlich vorkommt. Der Beleg ist aber nichts
  wert, und in 07 ist bei mehreren Treffern unklar, welche Stelle markiert wird. Vorschlag: Das Zitat
  muss auf Wortgrenzen beginnen und enden und außer Zahlen mindestens ein Wort enthalten. Sonst entsteht
  `info` „Zitat zu kurz“. Der Mensch sollte das vorher im Plan unter „Zitatprüfung“ festlegen.

  Erledigt: Zitat gilt nur an Wortgrenzen (Zahlen mitten in längeren Zahlen zählen nicht) und mit mindestens 3 Wörtern als Beleg, sonst `info` „Zitat zu kurz als Beleg“; nicht im Text bleibt „Zitat nicht im Text gefunden“. Gilt auch für `methodology`. Tests: „20“ allein, „0 ha“ gegen „100.0 ha“, Wortende, gültiges 3-Wort-Zitat. Plan („Zitatprüfung“) und CLAUDE.md ergänzt; Zitate in `examples/pdd-section.md` haben mindestens 3 Wörter (End-to-end-Test grün).

## Hinweis

- [x] **H1** `src/carbon_preaudit/preaudit/compare.py:39`: `\d+` trifft auch Ziffern in Wörtern.
  Aus „tCO2e“ wird der Kandidat 2, aus „VM0047“ der Kandidat 47. Ein Zitat mit „tCO2e“ belegt also
  jeden behaupteten Wert 2. Vorschlag: `(?<![^\W\d_])` oder ein vergleichbares Lookbehind, das nur
  Ziffern ohne vorangestellten Buchstaben zulässt, und dazu ein Test.

  Erledigt: Ziffern, die an Buchstaben grenzen („tCO2e“, „VM0047“), sind keine Kandidaten; Tests ergänzt.

- [x] **H2** `src/carbon_preaudit/preaudit/compare.py:55-86`: Das Verhalten in drei Fällen ist weder
  dokumentiert noch getestet:
  - Vorzeichen fallen weg. Aus „-5 %“ ist 5 belegt, −5 dagegen nicht.
  - Bei Bereichen wie „8,000–9,000“ sind beide Enden einzeln belegt, verglichen wird also gegen ein Ende,
    ohne Hinweis darauf, dass der Text einen Bereich nennt.
  - Wissenschaftliche Notation wie „1.2e4“ ergibt die Kandidaten {1.2, 4}, 12000 gilt also als nicht
    belegt. Diese Richtung ist sicher.

  Vorschlag: Das Verhalten im Plan unter „Wertprüfung“ in einem Satz festhalten und je einen Test
  ergänzen.

  Erledigt: Vorzeichen bleibt („-5 %“ ist −5, nicht nach Buchstabe/Ziffer); Bereiche und wissenschaftliche Notation (kein Kandidat) im Docstring von `number_candidates` und im Plan dokumentiert, je ein Test.

- [x] **H3** `src/carbon_preaudit/preaudit/extractor.py:93`: Das Escaping trifft nur genau
  `</document>`. Varianten wie `</Document>` und `</document >` bleiben stehen. Die Prüfung selbst wird
  dadurch nicht schwächer, denn `compare` prüft gegen den Originaltext, und ein Zitat, das über die
  ersetzte Stelle reicht, fällt als „Zitat nicht im Text gefunden“ auf. Das ist die sichere Richtung.
  Vorschlag: Ohne Rücksicht auf Groß- und Kleinschreibung per Regex ersetzen, etwa `</\s*document\s*>`.

  Erledigt: Escaping per Regex `</\s*document\s*>`, case-insensitive; parametrisierter Test.

- [x] **H4** `src/carbon_preaudit/preaudit/extractor.py:15`, `:113-114`: `fallbacks="default"` mit
  Beta-Header lässt bei einer Ablehnung serverseitig ein anderes Modell antworten. Davon steht nichts im
  Plan, und welches Modell geantwortet hat (`response.model`), wird nirgends festgehalten. Für Evals
  (06) ist dann nicht nachvollziehbar, welches Modell welches Ergebnis geliefert hat. Vorschlag: Die
  Fallbacks weglassen oder `response.model` zurückgeben bzw. loggen. Außerdem im Plan festhalten.

  Erledigt: `fallbacks="default"` bleibt; `ClaimedValues.extracted_by` (optional, Default None) wird vom `AnthropicExtractor` mit `response.model` gesetzt, `FakeExtractor` lässt es None. Plan (Modelltabelle, Extractor) ergänzt, Test geschrieben.

- [x] **H5** `src/carbon_preaudit/preaudit/extractor.py:116`: Ohne API-Key wirft `parse()` einen
  `TypeError` („Could not resolve authentication method“), andere SDK-Fehler als `anthropic.AnthropicError`.
  Beides kommt ungefangen an `ExtractionError` vorbei. In 07 führt das zu einem 500er. Vorschlag:
  `anthropic.AnthropicError` statt `APIError` abfangen und den Key beim Bau des Clients prüfen.

  Erledigt: `anthropic.AnthropicError` und das vom SDK bei fehlendem Key geworfene `TypeError` werden beim Aufruf zu `ExtractionError`, ebenso `AnthropicError` beim Erzeugen des Clients; Tests ergänzt.

- [x] **H6** `src/carbon_preaudit/preaudit/compare.py:143`, `:148-149`: Mit tC-Diagnose lautet die
  Meldung „Brutto-Menge (tCO₂e): behauptet 2.279,0 tCO₂e, … Vermutlich tC statt tCO₂e.“ Die Einheit beim
  behaupteten Wert widerspricht damit der Diagnose im selben Satz. Vorschlag: Bei dieser Diagnose die
  Einheit beim behaupteten Wert weglassen oder „tC“ schreiben.

  Erledigt: Bei der tC-Diagnose steht beim behaupteten Wert „tC“ („behauptet 272,7 tC, berechnet 1.000,0 tCO₂e“); Test ergänzt.

- [x] **H7** `src/carbon_preaudit/preaudit/compare.py:1`, `src/carbon_preaudit/domain/models.py:164-174`:
  Die Logik in `compare.py` hat keine Version, weil `CALC_VERSION` nur `calc/` abdeckt, und `Finding`
  trägt weder `run_hash` noch `params_version`. Für Schritt 05 verlangt der Plan das nicht. Für 06
  (Ergebnisse unter `evals/results/`) und 07 sollte aber festgelegt werden, wie ein Befund einer
  Code-Version zugeordnet wird (Leitprinzip 2).

  Erledigt: als offene Frage im Plan (Abschnitt „Offene Fragen“).

- [x] **H8** `docs/plans/01-architecture.md:265`: In „Fortschritt“ ist 05 nicht abgehakt (DoD „Plan-Datei
  aktualisiert“). Spätestens zur Abnahme nachziehen.
  Erledigt: 05 ist im Fortschritt abgehakt.

## Fazit

Die deterministische Bewertung stimmt mit Regeltabelle, Toleranzen, Schweregraden und Diagnosen überein,
und der Extractor rechnet nicht. Leitprinzip 1 ist eingehalten. Nicht abnahmefähig ist der Schritt wegen
K1 (Verstoß gegen ADR 0002, braucht eine Entscheidung des Menschen). Nach Behebung von K1 ist er
abnahmefähig. W1 bis W4 sollten vor 06 erledigt sein, weil sie Precision und Recall der Evals direkt
verfälschen.
