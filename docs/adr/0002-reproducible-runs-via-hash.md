# ADR 0002: Reproduzierbare Läufe über Hash

Status: angenommen · Datum: 2026-10-29

## Kontext

Ein Befund ist nur so belastbar wie die Berechnung, auf die er sich bezieht. Wer einen Lauf später erneut
ausführt, muss dasselbe Ergebnis bekommen und das auch prüfen können. Ergebnisse hängen ab von den
Eingaben, den Parametern (Allometrie-Koeffizienten, Kohlenstoffanteil, Default-Holzdichte, Puffer) und der
Rechenlogik. Ein Git-SHA als Code-Version ist ungeeignet: Ein uncommitteter Stand trägt den SHA des letzten
Commits, Docker-Images werden ohne `.git` gebaut, und jede Doku-Änderung würde den Hash verändern.

## Entscheidung

- `run_hash` ist SHA-256 über ein kanonisches JSON mit:
  - dem Polygon (Koordinaten wie geliefert),
  - allen Bäumen, sortiert nach `(plot_id, tree_id)`, mit `plot_area_m2` und `wood_density_g_cm3`
    (fehlend als `null`, nicht durch den Default ersetzt),
  - `buffer_pct`,
  - `PARAMS_VERSION` aus `calc/params.py`,
  - `CALC_VERSION` aus `calc/version.py`.
- Kanonisch heißt: `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, Zahlen
  als `float` geparst. „12“ und „12.0“ in der CSV ergeben denselben Hash.
- Jede Änderung eines Werts in `params.py` erhöht `PARAMS_VERSION`. Jede Logikänderung in `calc/` erhöht
  `CALC_VERSION`.
- Durchsetzung: Golden-Tests führen ihre Sollwerte nach Version, z. B. `GOLDEN = {"1": {...}}`, und prüfen
  `GOLDEN[CALC_VERSION]`. Eine Logikänderung macht den Test rot. Neue Sollwerte lassen sich nur unter einer
  neuen Version eintragen, damit ist die Erhöhung erzwungen.
- `created_at` und andere Metadaten gehen nicht in den Hash ein.

## Konsequenzen

- Gleiche Eingaben, gleiche `PARAMS_VERSION` und gleiche `CALC_VERSION` ergeben dasselbe Ergebnis und
  denselben Hash, unabhängig von Zeilenreihenfolge und Zahlenformat in der CSV.
- Der Hash dient als Primärschlüssel für gespeicherte Läufe; erneutes Speichern ist idempotent.
- Ein Refactoring ohne Ergebnisänderung braucht keine neue `CALC_VERSION`, weil die Golden-Tests grün bleiben.
- Die Versionsdisziplin hängt an den Golden-Tests. Ihre Abdeckung muss jeder Review prüfen.
- Unterschiede durch Plattform-Floats sind theoretisch möglich, aber der Hash geht über die Eingaben, nicht
  über das Ergebnis. Er bleibt deshalb stabil.
