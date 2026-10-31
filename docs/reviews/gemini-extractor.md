# Review: Gemini-Extractor

Geprüft: uncommittete Änderungen auf `feat/gemini-extractor` gegen `master` (4796b67):
`src/carbon_preaudit/preaudit/extractor.py`, `tests/test_extractor.py`, `docs/adr/0008-gemini-as-default-extractor.md`,
`docs/plans/01-architecture.md`, `CLAUDE.md`, `README.md`, `.env.example`, `pyproject.toml` ·
Grundlage: `CLAUDE.md`, ADR 0001, ADR 0008, Plan-Abschnitt „Extractor“, SDK google-genai 2.34.0 in `.venv`

pre-commit und die 246 Tests waren laut Auftrag bereits grün und sind nicht erneut gemeldet. Das Verhalten
bei Netzwerkfehlern habe ich mit einem `genai.Client` gegen `http://127.0.0.1:9` geprüft, also ohne
externes Netzwerk.

Ohne Befund geprüft:
- `generate_content(model=…, contents=str, config=GenerateContentConfig(…))` ist korrekt verwendet.
  `system_instruction` (str), `response_mime_type`, `response_json_schema` und `max_output_tokens` sind
  Felder von `GenerateContentConfig`. `response_json_schema` geht unverändert als `responseJsonSchema` an die
  API (`_transformers.t_json_schema` gibt den Wert unverändert zurück).
- Schema: `ExtractionOutput` ist flach und erzeugt kein `$defs` und kein `$ref`. Es enthält nur `anyOf` mit
  `{"type": "null"}`, `title`, `description`, `required` und `type: object`. Diese Teilmenge unterstützt das
  Feld `response_json_schema` (JSON Schema, nicht das OpenAPI-`Schema`).
- Prüfreihenfolge `block_reason` → keine Kandidaten → `finish_reason` (MAX_TOKENS, dann alles außer
  STOP/None) → leerer Text → JSON/Schema ist vollständig. `response.text` lässt Thought-Parts weg, und ein
  Kandidat ohne `content` endet als „empty“.
- `vertexai=False` ist sinnvoll. Es überstimmt ein gesetztes `GOOGLE_GENAI_USE_VERTEXAI=true` aus der
  Umgebung (geprüft: `Client(vertexai=False).vertexai is False`) und stellt den AI-Studio-Pfad sicher.
- Ohne `retry_options` versucht das SDK genau einmal (`retry_args(None)` → `stop_after_attempt(1)`).
  Es gibt also keine versteckten Wiederholungen.
- Die Tests bauen echte `GenerateContentResponse`/`Candidate`/`Part`-Objekte, und `.text`,
  `.prompt_feedback` und `.candidates` laufen über den echten SDK-Code. Kein Test geht über das Netzwerk.
  `test_gemini_missing_api_key` löscht beide Key-Variablen.
- Leitprinzip 1 ist unberührt: Gemini liefert nur Werte und Zitate, `compare.py` ist unverändert.
- README: Der Abschnitt „API-Key“ beschreibt weiterhin nur das Setup, mit einem Befehl pro Block.

## Kritisch

Keine.

## Wichtig

- [x] **W1** `src/carbon_preaudit/preaudit/extractor.py:182`: Nur `genai_errors.APIError` wird in
  `ExtractionError` übersetzt. Netzwerkfehler gehen am Wrapper vorbei. Der Probelauf gegen einen geschlossenen
  Port wirft `httpx.ConnectError`, und bei einem Timeout wäre es `httpx.TimeoutException` (bzw. die
  `httpx2`-Varianten, die das SDK ebenfalls verwendet). Eine nicht-JSON-Antwort des Servers wirft
  `genai_errors.UnknownApiResponseError`, und das ist ein `ValueError`, kein `APIError`. Beim
  `AnthropicExtractor` sind Verbindungsfehler `anthropic.APIConnectionError ⊂ anthropic.APIError` und
  werden gewrappt. Der Gemini-Pfad verletzt damit den Vertrag „ExtractionError: API error, refusal, or
  unusable output“, und ein Aufrufer, der nur `ExtractionError` fängt, bekommt einen 500er.
  Vorschlag: zusätzlich `genai_errors.UnknownApiResponseError`, `httpx.HTTPError` und `httpx2.HTTPError`
  fangen (`httpx`/`httpx2` dann als direkte Abhängigkeit, oder beide über das SDK importieren). Dazu ein
  Test, in dem der Fake-Client `httpx.ConnectError` wirft.
  Erledigt: `httpx2.HTTPError` (das SDK nutzt `httpx2`, schon direkte Abhängigkeit) und `UnknownApiResponseError` werden zu `ExtractionError` mit `from e`; Tests mit `ConnectError` und `UnknownApiResponseError`.

## Hinweis

- [x] **H1** `src/carbon_preaudit/preaudit/extractor.py:162`, `docs/plans/01-architecture.md` (Abschnitt
  Anbieterwahl), `README.md` „API-Key“: Der Vorrang ist nicht dokumentiert. Das SDK nimmt `GOOGLE_API_KEY`
  vor `GEMINI_API_KEY` (`_api_client.get_env_api_key`) und loggt dabei nur eine Warnung. Ist in der Shell
  ein `GOOGLE_API_KEY` für einen anderen Dienst gesetzt, wird der Key aus `.env` stillschweigend
  überstimmt. Vorschlag: Vorrang in Code-Kommentar, Plan und README in je einem Satz nennen, oder den Key
  explizit übergeben (`api_key=os.environ.get("GEMINI_API_KEY")`).
  Erledigt: Vorrang von `GOOGLE_API_KEY` in README, Code-Kommentar, ADR 0008 und Plan genannt.
- [x] **H2** `src/carbon_preaudit/preaudit/extractor.py:203`: `extracted_by` ist der angefragte Name. Ohne
  Fallback ist das vertretbar, aber die Antwort liefert `response.model_version` mit der tatsächlich
  verwendeten Version. Bei einem Alias in `CARBON_PREAUDIT_MODEL` (etwa `…-latest`) belegt erst diese
  Version, welches Modell extrahiert hat. Vorschlag: `response.model_version or self._model`. Die
  Begründung im Plan dann entsprechend anpassen.
  Erledigt: `extracted_by = response.model_version or self._model`, Test ergänzt, Plan angepasst.
- [x] **H3** `src/carbon_preaudit/preaudit/extractor.py:20-21,179`: `MAX_TOKENS` und der Kommentar zum
  Thinking beziehen sich auf das Claude-Modell. Für Gemini ist kein `thinking_config` gesetzt, also gilt
  das Thinking-Default des Modells, und die Thinking-Tokens zählen gegen `max_output_tokens`. Ein hohes
  Default-Budget führt dann zu `MAX_TOKENS`-Abbrüchen. Vorschlag: `thinking_config=ThinkingConfig(thinking_level=…)`
  explizit setzen oder eine eigene Gemini-Konstante mit Kommentar anlegen.
  Erledigt: `ThinkingConfig(thinking_level=LOW)` gesetzt (MINIMAL nicht von jedem Gemini-3-Modell unterstützt, `thinking_budget` ist modellabhängig); `MAX_TOKENS`-Kommentar gilt nun für beide Anbieter; Test prüft das Level.
- [x] **H4** `src/carbon_preaudit/preaudit/extractor.py:167`: `CARBON_PREAUDIT_MODEL` gilt für beide
  Anbieter. Wer es für Anthropic auf `claude-opus-5-5` setzt und danach den Provider wechselt, schickt
  einen Claude-Namen an Gemini, und das endet in einem API-Fehler. Vorschlag: im Plan bzw. in
  `.env.example` vermerken, dass der Wert zum gewählten Anbieter passen muss.
  Erledigt: Hinweis in `.env.example` und im Plan, keine Code-Logik.
- [x] **H5** `tests/test_extractor.py:328`: `test_gemini_request_parameters` prüft `max_output_tokens`
  nicht. Die Anthropic-Tests prüfen das Gegenstück. Vorschlag: `assert config.max_output_tokens == MAX_TOKENS`.
  Erledigt: Test prüft `max_output_tokens == MAX_TOKENS`.
- [x] **H6** `docs/adr/0001-ai-extracts-code-evaluates.md:17`: Dort steht weiterhin „`AnthropicExtractor`
  ist die einzige Stelle mit Netzwerkzugriff“. ADR 0008 ergänzt diese Aussage, sagt das aber nicht.
  Vorschlag: In ADR 0008 einen Satz aufnehmen, dass sie ADR 0001 in diesem Punkt ergänzt (beide
  LLM-Extractors sind die einzigen Stellen mit Netzwerkzugriff). ADR 0001 selbst bleibt unverändert.
  Erledigt: ADR 0008 nennt die Ergänzung zu ADR 0001, ADR 0001 sagt nun „nur die Extractor-Implementierungen“.

## Fazit

Der Gemini-Aufruf ist gegen SDK 2.34.0 korrekt, das Schema ist kompatibel, und die Antwortprüfung ist
vollständig und mit echten Antwortobjekten getestet. Nach Behebung von W1 (Netzwerk- und Parse-Fehler in
`ExtractionError` übersetzen) ist die Änderung abnahmefähig. Die Hinweise betreffen vor allem Doku und
Nachvollziehbarkeit.
