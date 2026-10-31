# Eval-Bericht

- Zeitpunkt (UTC): 2026-10-31 12:04:56
- Anbieter: gemini
- Modell (angefragt): gemini-3.5-flash-lite
- Modell (geantwortet): gemini-3.5-flash-lite
- run_hash: `be6521755e0922c72503bf5782cb6de3b44856c975f131a0239af69c83993f3a`
- PARAMS_VERSION: 1
- CALC_VERSION: 1
- App-Version: 0.1.0
- Git-Commit: a057e3c
- Prompt-Hash (SHA-256, 12 Zeichen): 3ebd19b1d751
- Fälle: 12
- Fehler (Extraktion fehlgeschlagen): 0

Bewertet: 12 von 12 Fällen. Kein Fall mit Extraktionsfehler.

## Je Feld

| Feld | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| project_area_ha | 3 | 0 | 0 | 100 % | 100 % |
| tco2e_gross | 1 | 0 | 0 | 100 % | 100 % |
| tco2e_net | 1 | 0 | 0 | 100 % | 100 % |
| buffer_pct | 3 | 0 | 0 | 100 % | 100 % |
| methodology | 1 | 0 | 0 | 100 % | 100 % |
| **gesamt** | 9 | 0 | 0 | 100 % | 100 % |

## Diagnosen

| Erwartet | Richtig | Unerwartet |
|---|---|---|
| 2 | 2 | 0 |

## Je Fall

Format: field/severity/diagnosis

| Fall | Erwartet | Tatsächlich | Ergebnis |
|---|---|---|---|
| area-01 | project_area_ha/major/– | project_area_ha/major/– | ✓ |
| area-02 | project_area_ha/major/– | project_area_ha/major/– | ✓ |
| area-03 | project_area_ha/major/– | project_area_ha/major/– | ✓ |
| buffer-01 | buffer_pct/major/– | buffer_pct/major/– | ✓ |
| buffer-02 | buffer_pct/major/– | buffer_pct/major/– | ✓ |
| clean-01 | – | – | ✓ |
| clean-02 | – | – | ✓ |
| clean-03 | – | – | ✓ |
| missing-01 | buffer_pct/info/– | buffer_pct/info/– | ✓ |
| missing-02 | methodology/info/– | methodology/info/– | ✓ |
| tonnes-swap-01 | tco2e_net/critical/gross_net_swapped | tco2e_net/critical/gross_net_swapped | ✓ |
| tonnes-tc-01 | tco2e_gross/critical/tc_instead_of_tco2e | tco2e_gross/critical/tc_instead_of_tco2e | ✓ |
