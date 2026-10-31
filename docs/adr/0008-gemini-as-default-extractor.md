# ADR 0008: Gemini als Default-Extractor

Status: angenommen · Datum: 2026-10-31

## Kontext

Die Extraktion braucht ein LLM. Der Mensch hat einen Key aus Google AI Studio, aber keinen Anthropic-Key
zur Hand. Ein Aufruf über den AI-Studio-Key ist einfach: ein API-Call mit One-Shot-Prompt, ohne Vertex.

## Entscheidung

- Gemini ist der Default-Anbieter (`GeminiExtractor`, Modell `gemini-3.8-flash`). Der `AnthropicExtractor`
  bleibt und wird über `CARBON_PREAUDIT_PROVIDER=anthropic` gewählt. `make_extractor()` trifft die Auswahl.
- Leitprinzip 1 bleibt unberührt: Das LLM extrahiert nur Werte und Zitate, jede Berechnung und Bewertung
  passiert in Python (ADR 0001).
- Der Anbieter ist austauschbar, weil das `Extractor`-Protocol ihn kapselt. Prompt, `<document>`-Wrapping
  und Ausgabemodell sind für beide Anbieter gleich.

## Konsequenzen

- Die Evals messen die Extraktion pro Anbieter. Precision und Recall gelten für das jeweilige Modell und
  sind nicht anbieterübergreifend vergleichbar, solange die Anbieter nicht getrennt ausgewiesen werden.
- Der Refusal-Fallback (`fallbacks="default"`) gilt nur für Anthropic. Bei Gemini enden Blockierung,
  Abbruch und leere Antwort in `ExtractionError`.
- Die ADR ergänzt ADR 0001: Netzwerkzugriff gibt es nur in den Extractor-Klassen (`AnthropicExtractor`,
  `GeminiExtractor`).
- Das SDK nimmt `GOOGLE_API_KEY` vor `GEMINI_API_KEY`, wenn beide gesetzt sind, und loggt nur eine Warnung.
- Eine zusätzliche Abhängigkeit: `google-genai`.
