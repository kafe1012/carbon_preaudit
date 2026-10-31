# Vorlagen

## audit/findings.md

Übersicht zuerst, dann alle Findings nach Kategorie (K1 bis K12), innerhalb der Kategorie nach Fundort.
Keine Sortierung nach Wichtigkeit, keine Hervorhebung einzelner Findings als empfohlen. Titel neutral formulieren.

```
# Findings

## Übersicht
| Kategorie | Anzahl | kritisch | hoch | mittel | niedrig | davon „zu prüfen“ |
|-----------|--------|----------|------|--------|---------|-------------------|

## K1 – Verschluckte Fehler und stille Fallbacks

### F-<Nr> – <neutraler Kurztitel>
- Kategorie: K<n>
- Ort: <Datei>:<Zeile>
- Schweregrad: kritisch | hoch | mittel | niedrig
- Sicherheit: belegt | wahrscheinlich | zu prüfen
- Beleg: <kurzer Codeauszug oder Beschreibung>
- Auswirkung: <was kann schiefgehen, sachlich>
- Möglicher Korrekturansatz: <technisch, ggf. mehrere Optionen>
- Verhaltensänderung bei Korrektur: ja | nein  (bei ja: wer ist betroffen?)
- Abhängigkeiten: <andere Findings oder Codestellen, die eine Korrektur mitbetrifft>
- Aufwand: S | M | L

## Bewusst nicht als Finding gewertet
- <Datei>:<Zeile> – <Suchmuster-Treffer> – <warum begründet>

## Nicht geprüft
- <Kategorie oder Bereich> – <warum nicht oder nur teilweise>
```

Schweregrad ist eine sachliche Einstufung der Auswirkung, keine Empfehlung:
- **kritisch:** Sicherheitslücke, Secret, erfundenes Package, Datenverlust oder -verfälschung
- **hoch:** falsche Ergebnisse möglich, verdeckte Fehler, Tests ohne Aussagekraft für Kernlogik
- **mittel:** Wartbarkeit deutlich beeinträchtigt, absehbare Folgefehler
- **niedrig:** Stil, Rauschen, kosmetisch

## audit/decisions.md

Alle Finding-IDs, Spalte „Entscheidung“ leer. Wird nur vom Menschen ausgefüllt.

```
# Entscheidungen

Mögliche Entscheidungen: korrigieren | nicht korrigieren | zurückstellen | klären

| Finding | Titel | Schweregrad | Entscheidung | Anmerkung |
|---------|-------|-------------|--------------|-----------|
| F-1     | ...   | hoch        |              |           |
```

## audit/summary.md (nur nach Teil B)

```
# Audit-Zusammenfassung

## Überblick
<3–5 Sätze, sachlich: Anzahl Findings, Verteilung, was auf Entscheidung des Menschen korrigiert wurde>

## Findings nach Kategorie
| Kategorie | Gefunden | Freigegeben | Korrigiert | Nicht korrigiert / zurückgestellt |
|-----------|----------|-------------|------------|-----------------------------------|

## Korrigiert (laut Freigabe)
- F-<Nr> – <Titel> – Commit <hash> – Nachweis: <wie verifiziert>

## Freigegeben, aber nicht abgeschlossen
- F-<Nr> – <Titel> – <Grund, z. B. Rückfrage offen, Test nach Korrektur rot>

## Neu entdeckt während der Korrektur
- F-<Nr> – <Titel> – Entscheidung offen

## Verhaltensänderungen
- F-<Nr> – <was sich für Aufrufer ändert>

## Baseline-Vergleich
- Tests vorher/nachher: <x/y> → <x/y>
- Lint/Typecheck vorher/nachher: <Anzahl Meldungen>

## Nicht verifiziert
- <Was> – <warum nicht prüfbar>

## Getroffene Annahmen
- <Annahme>
```
