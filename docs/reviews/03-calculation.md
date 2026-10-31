# Review 03: Berechnungslauf

Geprüft: uncommittete Änderungen auf `feat/03-calculation` (`src/carbon_preaudit/domain/*`,
`src/carbon_preaudit/calc/*`, `tests/helpers.py`, `tests/test_calc_golden.py`, `tests/test_area.py`,
`tests/test_hash.py`, `tests/test_inputs.py`, `tests/test_examples_run.py`) ·
Grundlage: `docs/plans/01-architecture.md` (Module, Konstanten, Domänenmodelle, Berechnungslauf,
DoD „03 Berechnungslauf“), `CLAUDE.md`, `DOMAIN.md`, ADR 0001, ADR 0002

Selbst ausgeführt: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` (0 Fehler)
und `uv run pytest` (80 grün). Die Randfälle unten habe ich mit einem Skript gegen `parse_inputs`,
`calculate` und `run_hash` geprüft. Die Ergebnisse stehen jeweils dabei.

## Kritisch

- [x] **K1** `src/carbon_preaudit/calc/inputs.py:72-83`, `src/carbon_preaudit/calc/area.py:18-21`,
  `src/carbon_preaudit/domain/models.py:41-46`: Ungültige Geometrien laufen still durch und liefern
  falsche Lauf-Ergebnisse, die trotzdem einen gültigen Hash tragen. Geprüft:
  - Breite außerhalb von ±90° (`[[0,90],[1,90],[1,95],[0,95],[0,90]]`): `project_area_ha = nan`, und
    damit sind auch brutto und netto `nan`. `CalculationRun` nimmt `nan` an, weil die Ergebnisfelder
    kein `allow_inf_nan=False` haben.
  - Ein Loch, das größer ist als der Außenring: `project_area_ha < 0`, `tco2e_net = -6755,86`.
    `area.py:21` zieht jedes Loch ab und prüft weder, dass es kleiner ist als der Außenring, noch
    dass das Ergebnis positiv ist.
  - Ein entarteter Ring (`[[0,0],[1,1],[0,0],[0,0]]`) und eine symmetrische Schleife
    (`[[0,0],[0.01,0.01],[0.01,0],[0,0.01],[0,0]]`) ergeben je 0 ha und damit 0 tCO₂e, ohne Fehler.
    Eine unsymmetrische Schleife liefert eine positive, aber falsche Fläche, weil
    `polygon_area_perimeter` die vorzeichenbehafteten Teilflächen addiert.
  - Länge 400° wird angenommen (123,09 ha, also stillschweigend modulo 360).
  Erledigt: `InvalidGeometryError(InputError)`; der Parser prüft lon/lat-Bereich, mindestens 3 verschiedene Punkte und Selbstüberschneidung je Ring (alle nicht benachbarten Segmentpaare, reines Python). `polygon_area_ha` wirft bei Loch >= Außenring und bei Fläche nicht endlich oder <= 0. Float-Felder aller Eingabe- und Ergebnismodelle haben `allow_inf_nan=False`, `OverflowError` wird zu `InvalidValueError`. Tests in `tests/test_inputs.py`.

  Ein Lauf mit `nan` oder negativen Tonnen ist das Gegenteil eines belegbaren Ergebnisses
  (Leitprinzip 3). Im Pre-Audit (Schritt 05) würde `abs(c − k) / k` damit `nan` oder ein falsches
  Vorzeichen liefern. Vorschlag:
  (a) In `_parse_polygon` (und im Modell `GeoJSONPolygon`) Länge in [−180, 180] und Breite in
  [−90, 90] prüfen, sonst `InvalidGeoJSONError`.
  (b) Eine eigene Exception, z. B. `InvalidGeometryError(InputError)`, wenn ein Loch nicht kleiner
  ist als der Außenring oder `project_area_ha` nicht endlich und > 0 ist. Wenn `calc/` keine
  Exceptions aus `inputs.py` importieren soll, gehört die Prüfung in `parse_inputs`.
  (c) Selbstüberschneidungen mit einer einfachen Schnittprüfung über alle Segmentpaare in reinem
  Python erkennen. Wenn das zu viel ist, den Fall unter „Offene Fragen“ im Plan und in „Bewusst
  nicht enthalten“ aufnehmen. Dann fängt (b) wenigstens den 0-ha-Fall ab.
  (d) Die Float-Felder von `CalculationRun` und `PlotResult` auf `allow_inf_nan=False` setzen, als
  Netz für alles, was durchrutscht. Dazu je ein Test in `tests/test_inputs.py`.

## Wichtig

- [x] **W1** `src/carbon_preaudit/calc/inputs.py:106-125`: Zeilen mit mehr Feldern als Spalten im
  Header werden still akzeptiert. `csv.DictReader` legt die überzähligen Werte unter dem Schlüssel
  `None` ab, und niemand prüft das. Der typische Fall ist ein Dezimalkomma: Aus
  `P1,400,T1,12,5,15,0,6` (gemeint: D = 12,5, H = 15, ρ = 0,6) wird `dbh_cm=12.0`, `height_m=5.0`,
  `wood_density_g_cm3=15.0`. Das ist geprüft, und der Lauf rechnet ohne Warnung mit diesen Werten.
  Vorschlag: `if None in row: raise InvalidValueError(f"Line {line}: too many fields")`. Zu wenige
  Felder werden schon heute abgefangen (`height_m=''`). Dazu ein Test.
  Erledigt: Zeilen mit zu vielen oder zu wenigen Feldern werfen `InvalidValueError` mit Zeilennummer, Tests dazu.
- [x] **W2** `src/carbon_preaudit/calc/inputs.py:118-124`, `src/carbon_preaudit/domain/models.py:22-24`:
  `wood_density` hat keine Obergrenze. Eine Holzdichte in kg/m³ statt g/cm³ (`600` statt `0.6`)
  läuft durch und ergibt 7 265,67 statt 8,58 tCO₂e/ha, also etwa das 850-Fache. `DOMAIN.md`
  („Einheiten und Fallstricke“) nennt genau solche Einheitenfehler als Hauptrisiko. Der Plan
  verlangt nur „> 0“, insofern ist der Code planmäßig. Die Lücke ist aber fachlich relevant und lässt
  sich mit einer Zeile schließen. Bei extremen Werten (`dbh_cm=1e200`, JSON-Koordinate `10**400`)
  entsteht außerdem `OverflowError` statt einer eigenen Exception (`allometry.py:8`,
  `inputs.py:76`). Vorschlag: `MAX_WOOD_DENSITY_G_CM3 = 1.5` als Plausibilitätsgrenze nach
  `params.py`, mit Begründung im Plan. Das ist noch `PARAMS_VERSION` 1, weil nichts veröffentlicht
  ist. Werte darüber werfen `InvalidValueError` mit dem Hinweis „g/cm³ erwartet“. Grobe Obergrenzen
  für `dbh_cm` und `height_m` verhindern den Overflow. In `_parse_polygon` reicht ein
  `except OverflowError`.
  Erledigt: `MAX_WOOD_DENSITY_G_CM3 = 1.5` in `params.py` (PARAMS_VERSION bleibt "1"), Parser und `Tree` lehnen größere Werte ab (Hinweis auf g/cm3), Plan-Tabelle ergänzt. Overflow bei extremen Werten wird in `calculate` und beim Parsen zu `InvalidValueError`.
- [x] **W3** `src/carbon_preaudit/domain/models.py:17-54`: Die Modelle setzen die Regeln aus der
  Plan-Tabelle nicht durch: `plot_id` eindeutig, `tree_id` eindeutig je Plot, `Tree.plot_id` gleich
  `Plot.plot_id`. Das tut nur `parse_inputs`. Geprüft: `ProjectInputs` mit zwei Plots `"P"`
  (400 m² und 800 m²), doppelten Bäumen und `Tree.plot_id="X"` in Plot `"P"` wird angenommen.
  Bei doppelten Schlüsseln hängt der Hash dann von der Reihenfolge ab (`hashing.py:14-21` sortiert
  stabil nach `(plot_id, tree_id)`). `Tree.plot_id` geht weder in den Hash noch in die Rechnung ein
  und kann so beliebig falsch sein. Schritt 04 (Läufe aus der Datenbank laden) und Schritt 07 bauen
  `ProjectInputs` womöglich nicht über `parse_inputs`. Vorschlag: `model_validator`s in `Plot`
  (Bäume tragen dieselbe `plot_id`, `tree_id` eindeutig) und in `ProjectInputs` (`plot_id`
  eindeutig). Alternativ `Tree.plot_id` streichen, denn die Information steckt schon im Plot. Plots
  und Bäume sollten außerdem im Modell sortiert werden, nicht nur im Parser. Dann ist die
  Summationsreihenfolge in `run.py:32-33` immer dieselbe wie die Hash-Reihenfolge. In meinem Test
  mit 30 umsortierten Plots war das Ergebnis zwar zufällig bitgleich, garantiert ist das bei
  Float-Summen aber nicht.
  Erledigt: `Plot` prüft eindeutige `tree_id` und `Tree.plot_id == plot_id`, `ProjectInputs` prüft eindeutige `plot_id`, je ein Test. Sortierung im Modell habe ich nicht eingeführt (nicht beauftragt, der Parser sortiert weiterhin).
- [x] **W4** `tests/test_calc_golden.py:17-23`: Der Golden-Mechanismus erzwingt die
  Versionserhöhung nur teilweise:
  - `GOLDEN` ist nur nach `CALC_VERSION` geschlüsselt. Ändert jemand einen Wert in `params.py`,
    z. B. `CARBON_FRACTION`, wird der Test rot. Der naheliegende „Fix“ ist dann, `GOLDEN["1"]`
    anzupassen oder fälschlich `CALC_VERSION` zu erhöhen. Nichts erzwingt `PARAMS_VERSION`. Die
    Toleranzen und `EXPECTED_METHODOLOGY` deckt in Schritt 03 gar kein Test ab.
  - `GOLDEN` hält nur `agb_kg`, `tco2e` und `tco2e_per_ha` fest. `project_area_ha`, `tco2e_gross`,
    `tco2e_net` und `run_hash` prüft der Test nur relativ zu sich selbst (`:49-51`: `gross` gegen
    `run.project_area_ha`). Eine Änderung an `area.py` (Ellipsoid, Löcher) oder an der kanonischen
    Form in `hashing.py` ändert also das Ergebnis oder den Hash, ohne dass ein versionsgeführter
    Sollwert rot wird. Zur kanonischen Form gibt es überhaupt keinen festgehaltenen Hash.
  Erledigt: `GOLDEN["1"]` hat `project_area_ha`, `tco2e_gross`, `tco2e_net`, `run_hash`; neues `PARAMS_GOLDEN` mit Test gegen die aktuelle `PARAMS_VERSION`, dazu ein Test für die kanonische JSON-Form. ADR 0002 um die Regel „bestehende Einträge nie ändern“ ergänzt.

  Vorschlag: In `GOLDEN["1"]` für `SQUARE_001` auch `project_area_ha` (≈ 123,0907, unabhängig per
  Kleinzellenformel in `test_area.py` belegt), `tco2e_gross`, `tco2e_net` und den erwarteten
  `run_hash` eintragen. Dazu kommt ein zweiter, nach `PARAMS_VERSION` geschlüsselter Golden, der
  alle Werte aus `params.py` als Momentaufnahme hält (`PARAMS_GOLDEN = {"1": {"CHAVE_A": 0.0673,
  ...}}`). Er wird bei jeder Wertänderung ohne Versionserhöhung rot. Wichtig für ADR 0002: Auch so
  verhindert technisch nichts, dass jemand den Eintrag `"1"` vor Ort überschreibt. Der Satz „Neue
  Sollwerte lassen sich nur unter einer neuen Version eintragen“ stimmt nur zusammen mit der Regel,
  dass Reviews jede Änderung an bestehenden `GOLDEN`-Einträgen ablehnen. Das sollte in die ADR.

## Hinweis

- [x] **H1** `src/carbon_preaudit/calc/hashing.py:26-37`: Die kanonische Form normalisiert `-0.0`
  nicht. Ein Polygon mit `-0.0` als Koordinate und `parse_inputs(..., buffer_pct=-0.0)` ergeben
  jeweils einen anderen Hash als `0.0` (geprüft), bei gleichem Ergebnis. `-0.0` landet sogar als
  `buffer_pct` im `CalculationRun`. Vorschlag: In der kanonischen Form `float(x) + 0.0` verwenden,
  das macht `-0.0` zu `0.0`. Ohne Befund geprüft: `1e-7` und `0.0000001`, `4e2` und `400` hashen
  gleich, weil `json.dumps` `repr(float)` verwendet. `None` und ρ = 0,6 hashen verschieden. Das
  verlangt ADR 0002 so („fehlend als `null`“), und es ist richtig: Ändert sich der Default, ändert
  sich das Ergebnis, und das deckt `PARAMS_VERSION` im Hash ab. `test_hash.py:41-43` prüft es.
  Erledigt: `-0.0` wird im Hash zu `0.0` normalisiert (`float(x) + 0.0`), Test dazu.
- [x] **H2** `src/carbon_preaudit/calc/hashing.py:35-37`, ADR 0002: Laut ADR geht das Polygon mit
  „Koordinaten wie geliefert“ ein. Tatsächlich wird eine dritte Koordinate (Höhe) beim Parsen
  verworfen (`inputs.py:81`) und nicht gehasht. Das ist fachlich richtig, weil die Höhe nicht in
  die Rechnung eingeht, sollte aber in der ADR stehen. Ebenso ergeben ein anderer Startpunkt des
  Rings, eine andere Ringrichtung oder eine andere Reihenfolge der Löcher einen anderen Hash bei
  gleicher Fläche. Das passt zu „wie geliefert“, und der Hash ist nicht als Geometrie-Identität
  gedacht. Ein Satz dazu in der ADR beugt Missverständnissen vor.
  Erledigt: ADR 0002 hält fest, dass das Polygon wie geliefert gehasht wird (Ringstart, Richtung, Lochreihenfolge zählen, Höhe fällt weg), Test dazu.
- [x] **H3** `src/carbon_preaudit/calc/inputs.py:108-109`: IDs werden nicht Unicode-normalisiert.
  `"Pé"` als NFC und als NFD ergibt zwei verschiedene `plot_id`s und zwei verschiedene Hashes
  (geprüft). Exporte von macOS und Windows können sich genau darin unterscheiden. Vorschlag:
  `unicodedata.normalize("NFC", ...)` vor `strip()`, oder die Entscheidung dagegen in ADR 0002
  festhalten.
  Erledigt: IDs werden im Parser auf NFC normalisiert, Test mit NFC und NFD.
- [x] **H4** `src/carbon_preaudit/calc/inputs.py:99-103`: Eine CSV mit UTF-8-BOM (Excel, „CSV UTF-8“)
  scheitert mit `MissingColumnError: plot_id`, obwohl die Spalte da ist. Ein Header mit
  Leerzeichen (`plot_id, plot_area_m2, ...`, so geschrieben auch in `CLAUDE.md` unter Scope)
  scheitert mit vier fehlenden Spalten. Beides geht nicht still durch, ist für die Weboberfläche
  aber irreführend. Leerzeichen um die Werte werden schon korrekt entfernt (geprüft). Vorschlag:
  `csv_text.removeprefix("﻿")` und die Header-Namen strippen (`reader.fieldnames = [...]`).
  Erledigt: BOM wird entfernt, Header-Namen werden getrimmt, je ein Test.
- [x] **H5** `src/carbon_preaudit/calc/inputs.py:52-81`: Acht `# pyright: ignore[reportUnknown…]`
  verdecken implizite `Any` aus `json.loads`. Formal ist `CLAUDE.md` („keine `Any` in `src/`“)
  eingehalten, im Sinne der Regel aber nur knapp. Vorschlag: Die Rohstruktur mit einem Pydantic-
  `TypeAdapter` validieren, etwa für `{"type": Literal[...], "coordinates": list[list[list[float]]]}`.
  Der Typfehler wird dann in `InvalidGeoJSONError` übersetzt, und die Ignores fallen weg.
  Erledigt: Das Roh-GeoJSON wird mit Pydantic (`TypeAdapter` für die Hülle, `_RawPolygon` im Strict-Modus) validiert, alle `pyright: ignore` in `inputs.py` sind weg. Fehler werden zu `InvalidGeoJSONError`. Die eine `pyright: ignore` in `area.py` (pyproj ohne Typen) bleibt, sie gehört nicht zu diesem Befund.
- [x] **H6** `docs/plans/01-architecture.md:60` und `src/carbon_preaudit/domain/models.py:32`: Fachlich
  verzerrt die Regel „mindestens ein Baum je Plot“ den flächengewichteten Mittelwert nach oben. Ein
  gemessener Plot ohne Bäume gehört mit 0 tCO₂e in den Nenner, statt dass die CSV ihn nicht
  ausdrücken kann (`P3,400,,,,` wirft heute `InvalidValueError`). Der Code folgt hier dem Plan. Das
  ist kein Fehler des Schritts, gehört aber unter „Offene Fragen“ oder „Bewusst nicht enthalten“.
  Zur DoD „leerer Plot“: Getestet sind die CSV ohne Zeilen (`EmptyPlotsError`) und `Plot(trees=())`.
  Letzteres wirft Pydantics `ValidationError`, keine eigene Exception. Ein Test für eine Zeile mit
  leerer `tree_id` fehlt (`tests/test_inputs.py:94-108` prüft nur eine leere `plot_id`).
  Erledigt: Test für leere `tree_id` und für die Zeile `P3,400,,,,` ergänzt; `Plot(trees=())` bleibt `ValidationError`; baumlose Plots stehen im Plan unter „Offene Fragen“.
- [x] **H7** `docs/plans/01-architecture.md:246`: Der Plan ist noch nicht aktualisiert, 03 steht
  noch auf `[ ]` (DoD „Plan-Datei aktualisiert“). Spätestens vor dem PR nachziehen.
  Erledigt: 03 ist im Fortschritt abgehakt.

Ohne Befund geprüft:
- **Formeln und Einheiten:** Chave mit ρ in g/cm³, D in cm und H in m (`allometry.py:8`). kg wird
  durch 1000 geteilt, dann × 0,47 × 44/12. m² wird durch 10 000 zu ha. Fläche: Betrag je Ring
  (`area.py:15`), damit ist die Ringrichtung egal, auch bei Löchern mit derselben Richtung wie der
  Außenring (`test_area.py:39-48`).
- **Flächengewichtung und Puffer:** Σ tCO₂e / Σ ha über alle Plots (`run.py:32-34`), dann
  × `project_area_ha`. Puffer brutto × % / 100, netto = brutto − Puffer. Es wird nicht gerundet.
- **Handrechnung:** Kleinzelle am Äquator, d = 0,01°: (1,745329·10⁻⁴)² · 6 335 439,3 m · 6 378 137 m
  ≈ 1 230 907 m² = 123,09 ha. pyproj liefert 123,0907 ha. `test_area_weighted_across_plots`:
  3 · 0,343033 = 1,029098 tCO₂e auf 0,12 ha = 8,5758 tCO₂e/ha, stimmt.
- **Hash:** Er liest `params.PARAMS_VERSION` und `version.CALC_VERSION` zur Laufzeit, deshalb greift
  der Monkeypatch in `test_hash.py:46-55`. `sort_keys`, `separators` und `ensure_ascii=False` sind
  wie in der ADR. `created_at` gibt es noch nicht. Es geht nichts Überflüssiges ein, und alle
  rechenrelevanten Eingaben (Polygon samt Löchern, alle Baumwerte, Plotfläche, Puffer, Versionen)
  sind enthalten.
- **Reinheit und Konventionen:** `calc/` macht kein I/O (`inputs.py` arbeitet nur auf Strings),
  hat eigene Exceptions mit gemeinsamer Basis und kein nacktes `except`. pyright strict ist grün.
- **Scope:** Nichts aus Schritt 04 und später (kein `ClaimedValues`, kein `Finding`, kein Store).
  Kein LLM beteiligt.

## Fazit

Rechnung, Einheiten und Hash-Grundform sind korrekt und sauber getestet. Die Golden-Werte stimmen.
Ungültige Geometrien liefern aber still `nan`, 0 oder negative Tonnen (K1), und Dezimalkomma oder
Holzdichte in kg/m³ verfälschen das Ergebnis unbemerkt (W1, W2). Nach Behebung von K1 sowie W1 bis W4
ist der Schritt abnahmefähig.
