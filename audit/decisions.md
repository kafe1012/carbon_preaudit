# Entscheidungen

Mögliche Entscheidungen: korrigieren | nicht korrigieren | zurückstellen | klären

Die Spalte „Entscheidung“ füllt nur der Mensch aus. Korrigiert wird ausschließlich, was im Chat mit
Finding-ID freigegeben wird.

| Finding | Titel | Schweregrad | Entscheidung | Anmerkung |
|---------|-------|-------------|--------------|-----------|
| F-1 | `TypeError` beim Anthropic-Aufruf wird als Extraktionsfehler gemeldet | mittel | | |
| F-2 | Ignore-Kommentar für eine Regel, die pyright nicht kennt | niedrig | | |
| F-3 | Assertions über Literale statt über das System | niedrig | | |
| F-4 | Lokale Claude-Konfiguration mit Firmenname im Gemini-Commit | hoch | | |
| F-5 | Lokale Startkonfiguration im UI-Commit | niedrig | | |
| F-6 | Umbenennung öffentlicher Funktionen in `compare.py` im UI-Commit | niedrig | | |
| F-7 | Konstante `_M2_PER_HA` doppelt | niedrig | | |
| F-8 | Liste der fünf Felder an mehreren Stellen | niedrig | | |
| F-9 | Ringprüfung im Parser und im Modell | niedrig | | |
| F-10 | Auswahl des Default-Modells doppelt | niedrig | | |
| F-11 | Englische Fehlermeldungen in der deutschen Oberfläche | niedrig | | |
| F-12 | Laufzeit-Import aus einer Dev-Abhängigkeit | mittel | | |
| F-13 | Direkter Import einer nicht deklarierten Abhängigkeit | niedrig | | |
| F-14 | Anthropic-Pfad nie gegen die echte API gelaufen | mittel | | |
| F-15 | Commit-Angabe im Eval-Bericht passt nicht zum Lauf | mittel | | |
| F-16 | Strukturangaben in CLAUDE.md veraltet | niedrig | | |
| F-17 | README-Abschnitt „Bewusst nicht enthalten“ fehlt | niedrig | | |
| F-18 | Widersprüchliche Regel zur Erhöhung von `CALC_VERSION` | niedrig | | |
| F-19 | Fehler aus der Rechnung führen in `/check` zu HTTP 500 | hoch | | |
| F-20 | Mehrdeutige Zahlenlesart lässt Fehllesung als belegt durch | hoch | | |
| F-21 | `/check` ohne Zugriffsschutz und Begrenzung, jeder Aufruf kostet LLM-Tokens | mittel | | |
| F-22 | Neuer LLM-Client pro Anfrage | niedrig | | |
| F-23 | Mehrfache Git-Aufrufe in der Versionsprüfung | niedrig | | |
| F-24 | `sqlalchemy` deklariert, aber nicht verwendet | niedrig | | |
