# Domänenwissen: naturbasierte CO₂-Projekte

Referenz für alle Agenten. Bei fachlichen Fragen zuerst hier nachlesen.
Was hier nicht steht, nicht erfinden: als offene Frage im Plan notieren.

## Worum es geht

Projektentwickler setzen Klimaprojekte um, z. B. Aufforstung. Für nachweislich gebundenes CO₂
erhalten sie **Credits** (1 Credit = 1 Tonne CO₂-Äquivalent, tCO₂e) und verkaufen diese an Unternehmen.
Bis dahin ist es ein langer, dokumentenlastiger Weg mit unabhängiger Prüfung.

Das Kernproblem, das dieses Projekt adressiert: Zahlen im Projektdokument passen nicht zu den Daten.
Solche Inkonsistenzen findet sonst erst der Auditor, das kostet Zeit und Geld.

## Märkte

- **Pflichtmarkt** (z. B. EU-ETS): Verschmutzer müssen Zertifikate vorweisen. Nicht unser Thema.
- **Freiwilliger Markt (VCM):** Unternehmen kaufen Credits freiwillig für Klimaziele. Unser Thema.
- **Entnahme vs. Vermeidung:** Aufforstung entzieht der Luft CO₂ (Entnahme, gefragter).
  Waldschutz verhindert Emissionen (Vermeidung).

## Projekttypen (Nature-based Solutions)

| Typ | Kurz | Für uns |
| --- | --- | --- |
| ARR (Afforestation, Reforestation, Revegetation) | neue Wälder pflanzen | **Fokus** |
| Mangroven-/Feuchtgebiet-Restauration | Blue Carbon | später |
| REDD+ | Waldschutz | nicht im Scope |
| IFM | schonendere Waldbewirtschaftung | nicht im Scope |
| Bodenkohlenstoff | Landwirtschaft | nicht im Scope |

## Projektlebenszyklus

1. Idee und Machbarkeit
2. **PDD** (Project Design Document): beschreibt Fläche, Methode, Berechnung, Monitoring
3. **Validierung** des PDD durch eine Prüfstelle (**VVB**, Validation/Verification Body)
4. **Registrierung** beim Standard (z. B. Verra)
5. **Monitoring** über Jahre, Ergebnis im Monitoring Report
6. **Verifizierung** durch die VVB
7. **Ausgabe** (Issuance) der Credits, jeweils mit **Vintage** (Jahr der Bindung)
8. **Stilllegung** (Retirement), wenn ein Käufer den Credit nutzt; danach nicht erneut verwendbar

Dauer bis zur ersten Ausgabe: meist 1–3 Jahre, Projektlaufzeit 20–100 Jahre.
Findet die VVB Mängel, gibt es **CARs** (Corrective Action Requests). Weniger CARs = schneller zu Credits.

## Standards und Regeln

- **Verra VCS:** größter Standard. Methodologie für ARR: **VM0047**. Mangroven: VM0033.
- **Gold Standard:** zweiter großer Standard.
- **ICVCM Core Carbon Principles:** Qualitätslabel, das Käufer zunehmend verlangen.
- **CCB:** Label für Zusatznutzen (Biodiversität, Gemeinden).
- **EU CRCF:** EU-Rahmen zur Zertifizierung von CO₂-Entnahmen.
- **Pariser Abkommen, Artikel 6:** Handel zwischen Staaten, verhindert Doppelzählung.
- Eine Methodologie hat Versionen. Ein Projekt ist an eine Version gebunden.

## Integritätsbegriffe

| Begriff | Bedeutung |
| --- | --- |
| Additionality | Wäre es ohne Credit-Finanzierung auch passiert? Dann kein Klimanutzen. |
| Baseline | Was wäre ohne Projekt passiert? Der Klimanutzen ist die Differenz dazu. |
| Permanence | Bleibt das CO₂ dauerhaft gebunden (Brand, Abholzung)? |
| Leakage | Wird Schaden nur verlagert, z. B. Abholzung ins Nachbargebiet? |
| Buffer Pool | Ein Teil der Credits wird als Reserve einbehalten. Bei Verra über ein Risikotool bestimmt, typischerweise 10–20 %. |
| Uncertainty Deduction | Abzug für Messunsicherheit |
| Double Counting | Dieselbe Tonne darf nur einmal angerechnet werden |
| Land Eligibility (ARR) | Fläche darf in den 10 Jahren vor Projektstart **kein** Wald gewesen sein |

## Messung

- Feldmessung in **Plots** (Probeflächen, z. B. 400 m²): je Baum Brusthöhendurchmesser (**DBH**, cm),
  Höhe (m), Holzdichte (g/cm³)
- **Allometrische Gleichung** schätzt Biomasse aus diesen Werten, z. B. Chave et al. 2014:
  `AGB_kg = 0.0673 * (ρ * D² * H) ** 0.976` (ρ g/cm³, D cm, H m)
- Kohlenstoffanteil der Trockenbiomasse: **0.47**
- Umrechnung Kohlenstoff → CO₂: **× 44/12**
- Hochrechnung: Plot-Werte pro Hektar × Projektfläche
- **Satellitendaten:** NDVI zeigt Vegetationsveränderung, taugt aber nicht zur Biomasseschätzung
  (sättigt bei dichtem Wald). Für Biomasse: Radar, LiDAR, Höhenmodelle.
- **dMRV:** digitales Messen, Berichten, Verifizieren

## Einheiten und Fallstricke

- DBH in **cm**, Höhe in **m**, Fläche Plot in **m²**, Projektfläche in **ha** (1 ha = 10 000 m²)
- Biomasse in **kg** pro Baum, Ergebnisse in **t** (1 t = 1000 kg)
- **tC ≠ tCO₂e**: Faktor 44/12 ≈ 3,67. Häufigster Fehler in Dokumenten.
- **Brutto vs. netto:** netto = nach Pufferabzug. Texte vermischen das oft.
- Fläche geodätisch berechnen, nicht in Grad-Koordinaten.

## Was Auditoren prüfen (und unser Pre-Audit nachahmt)

- Stimmen Zahlen im Text mit Daten und Berechnung überein?
- Ist jede Zahl bis zur Rohquelle nachvollziehbar?
- Sind Pflichtangaben der Methodologie vorhanden?
- Werden Begriffe korrekt verwendet (brutto/netto, tC/tCO₂e)?

## Vereinfachungen in dieser Demo

Bewusst weggelassen, im README so benennen:
- Keine Baseline-Abzüge: wir rechnen den Bestand, nicht den Zuwachs gegenüber der Baseline
- Nur oberirdische Biomasse, kein Wurzel-, Tot- oder Bodenkohlenstoff
- Keine Unsicherheits- und Leakage-Abzüge
- Puffer als fester Prozentsatz statt Risikotool
- Holzdichte-Default 0,6 g/cm³ als Demo-Annahme, wenn die Messung fehlt; der Lauf weist aus,
  für wie viele Bäume der Default verwendet wurde
- Keine methodologiekonforme VM0047-Berechnung

## Begriffe für Code-Bezeichner

| Fachbegriff | Bezeichner |
| --- | --- |
| Projektfläche | `project_area_ha` |
| Brusthöhendurchmesser | `dbh_cm` |
| Oberirdische Biomasse | `agb_kg` |
| CO₂e brutto / netto | `tco2e_gross` / `tco2e_net` |
| Pufferanteil | `buffer_pct` |
| Jahrgang der Credits | `vintage` |
| Berechnungslauf | `CalculationRun` |
| Prüfbefund | `Finding` |
