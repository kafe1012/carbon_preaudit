# Entscheidungen

Mögliche Entscheidungen: korrigieren | nicht korrigieren | zurückstellen | klären

Die Spalte „Entscheidung“ füllt nur der Mensch aus. Korrigiert wird ausschließlich, was im Chat mit
Finding-ID freigegeben wird.

| Finding | Titel | Schweregrad | Entscheidung | Anmerkung |
|---------|-------|-------------|--------------|-----------|
| F-1 | `TypeError` beim Anthropic-Aufruf wird als Extraktionsfehler gemeldet | mittel | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-2 | Ignore-Kommentar für eine Regel, die pyright nicht kennt | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-3 | Assertions über Literale statt über das System | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-4 | Lokale Claude-Konfiguration mit Firmenname im Gemini-Commit | hoch | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-5 | Lokale Startkonfiguration im UI-Commit | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-6 | Umbenennung öffentlicher Funktionen in `compare.py` im UI-Commit | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-7 | Konstante `_M2_PER_HA` doppelt | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-8 | Liste der fünf Felder an mehreren Stellen | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-9 | Ringprüfung im Parser und im Modell | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-10 | Auswahl des Default-Modells doppelt | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-11 | Englische Fehlermeldungen in der deutschen Oberfläche | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-12 | Laufzeit-Import aus einer Dev-Abhängigkeit | mittel | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-13 | Direkter Import einer nicht deklarierten Abhängigkeit | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-14 | Anthropic-Pfad nie gegen die echte API gelaufen | mittel | zurückstellen | braucht echten API-Lauf (Mensch, 2026-10-31) |
| F-15 | Commit-Angabe im Eval-Bericht passt nicht zum Lauf | mittel | zurückstellen | braucht echten API-Lauf (Mensch, 2026-10-31) |
| F-16 | Strukturangaben in CLAUDE.md veraltet | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-17 | README-Abschnitt „Bewusst nicht enthalten“ fehlt | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-18 | Widersprüchliche Regel zur Erhöhung von `CALC_VERSION` | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-19 | Fehler aus der Rechnung führen in `/check` zu HTTP 500 | hoch | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-20 | Mehrdeutige Zahlenlesart lässt Fehllesung als belegt durch | hoch | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-21 | `/check` ohne Zugriffsschutz und Begrenzung, jeder Aufruf kostet LLM-Tokens | mittel | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-22 | Neuer LLM-Client pro Anfrage | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-23 | Mehrfache Git-Aufrufe in der Versionsprüfung | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-24 | `sqlalchemy` deklariert, aber nicht verwendet | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-25 | Extractor-Tests je Anbieter doppelt geschrieben | mittel | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-26 | Tests prüfen den Wortlaut des Prompts | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-27 | Zitat- und Belegregeln in drei Testdateien | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-28 | Parserfehler über die Weboberfläche erneut getestet | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-29 | Pydantic-Verhalten Feld für Feld getestet | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-30 | Beispieldaten an fünf Stellen end-to-end geprüft | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-31 | Tests ohne eigene Aussage | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 |
| F-32 | Container-Start laut README ohne API-Key | mittel |  | neu entdeckt bei F-21, Entscheidung offen |
| F-33 | Parametertabellen mit vielen gleichartigen Fällen | niedrig | korrigieren | Ansatz (a), freigegeben im Chat am 2026-10-31 („Ja, kürzen“) |
