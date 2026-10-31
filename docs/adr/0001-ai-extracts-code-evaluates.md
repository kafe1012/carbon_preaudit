# ADR 0001: KI extrahiert, Code bewertet

Status: angenommen · Datum: 2026-10-29

## Kontext

Das Pre-Audit soll Zahlen in einem PDD-Abschnitt gegen die eigene Berechnung prüfen. Fließtext ist
uneinheitlich: Zahlen stehen in Sätzen, mit Tausendertrennern, in Prozent oder als Bruchteil, manchmal in
tC statt tCO₂e. Ein LLM kann solche Werte gut finden. Ein LLM, das selbst rechnet oder bewertet, ist aber
nicht reproduzierbar, schwer testbar und liefert keine nachvollziehbare Begründung. Ein Auditor muss jeden
Befund bis zur Rohquelle nachvollziehen können.

## Entscheidung

- Das LLM liefert ausschließlich `ClaimedValues`: je Feld den Wert, wie er im Text steht, und ein wörtliches
  Zitat, oder `null`. Es rechnet nicht, rechnet keine Einheiten um und bewertet nicht.
- Der Zugriff läuft über ein eigenes Protocol `Extractor`. nur die Extractor-Implementierungen haben
  Netzwerkzugriff (ADR 0008), `FakeExtractor` dient Tests und Entwicklung. Kein LangChain.
- Toleranzen, Schweregrade, Diagnosen (tC statt tCO₂e, brutto/netto verwechselt) und die Methodologie-Regel
  liegen als reine Funktion in `preaudit/compare.py`, die Konstanten in `calc/params.py`.
- `compare()` prüft, ob jedes Zitat wörtlich im Text steht. Fehlt es, wird der Wert nicht verglichen und als
  `info`-Befund „Zitat nicht im Text gefunden“ gemeldet.

## Konsequenzen

- Die gesamte Bewertung ist ohne Netzwerk und ohne API-Key testbar; Unit-Tests nutzen nur `FakeExtractor`.
- Gleiche `ClaimedValues` und gleicher `CalculationRun` ergeben immer dieselben Befunde.
- Die Unsicherheit liegt allein in der Extraktion. Sie wird über Evals mit Precision und Recall gemessen,
  nicht behauptet.
- Halluzinierte Zitate führen nicht zu falschen Befunden, sondern zu einem sichtbaren Hinweis.
- Die tC-Diagnose funktioniert nur, wenn der Extractor nicht umrechnet. Das muss der Prompt sicherstellen
  und ein Eval-Fall prüfen.
- Der Extractor ist austauschbar (anderes Modell, Regex-Baseline), ohne dass `compare.py` sich ändert.
