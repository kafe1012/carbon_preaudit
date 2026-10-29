# Problem Statement: carbon-preaudit

Fachbegriffe, Einheiten und Fallstricke stehen in [DOMAIN.md](../DOMAIN.md).
Scope und Leitprinzipien stehen in [CLAUDE.md](../CLAUDE.md), die Umsetzung in
[Plan 01](plans/01-architecture.md).

## Problem

Ein Aufforstungsprojekt erhält Credits erst, wenn eine Prüfstelle (VVB) sein PDD validiert hat. Die Zahlen
im PDD-Text entstehen aber woanders: Das GIS-Team liefert das Flächenpolygon, das Feldteam die
Baummessungen, und daraus wird die CO₂-Bindung berechnet.

Text und Daten werden von verschiedenen Personen über Wochen und mehrere Versionen gepflegt und laufen
dabei unbemerkt auseinander. Das Polygon wird korrigiert, eine Messrunde kommt dazu oder der Puffer ändert
sich, nur der Text nicht überall. Hinzu kommen die typischen Fehler wie tC statt tCO₂e oder brutto statt
netto (siehe [DOMAIN.md, „Einheiten und Fallstricke“](../DOMAIN.md#einheiten-und-fallstricke)).

Meist findet erst die Prüfstelle solche Widersprüche. Jeder Befund wird ein CAR: nachbessern, neu
einreichen, erneut prüfen lassen. Das kostet Beratungs- und Prüfaufwand und verzögert die Ausgabe der Credits.
Von Hand ist der Abgleich mühsam, weil die Zahlen verstreut und uneinheitlich formuliert im Fließtext stehen
und die Berechnung jedes Mal neu nachvollzogen werden muss.

**Kernfrage:** Wie findet ein Projektentwickler Widersprüche zwischen PDD-Text und Projektdaten, bevor die
Prüfstelle sie findet, und zwar so belegt, dass er sie sofort beheben kann?

## Geplante Lösung

Ein Pre-Audit-Check übernimmt diese eine Prüfung der Prüfstelle vor der Einreichung:

1. **Code rechnet** aus Polygon und Messdaten Fläche, Tonnen brutto und netto sowie den Puffer, reproduzierbar mit Hash.
2. **KI liest** den PDD-Text und ordnet zu, welche Zahl wofür steht, jeweils mit wörtlichem Zitat. Die KI rechnet und bewertet nicht.
3. **Code vergleicht** die behaupteten Werte mit den berechneten. Toleranzen und Schweregrade sind fest vorgegeben.
4. **Befunde** nennen Feld, beide Werte, das Zitat und den Schweregrad, wo erkennbar mit Diagnose. Die Oberfläche markiert die Fundstellen im Text.

Begründung und Regeln: [ADR 0001](adr/0001-ai-extracts-code-evaluates.md) und
[ADR 0002](adr/0002-reproducible-runs-via-hash.md). Details zur Umsetzung stehen in
[Plan 01](plans/01-architecture.md). Was bewusst fehlt, steht in [CLAUDE.md](../CLAUDE.md#bewusst-nicht-im-scope)
und [DOMAIN.md, „Vereinfachungen“](../DOMAIN.md#vereinfachungen-in-dieser-demo).

## Erfolgskriterien

- Ein PDD-Abschnitt mit eingebautem Fehler wird mit dem richtigen Feld und Schweregrad gemeldet.
- Ein fehlerfreier Abschnitt erzeugt keinen Befund.
- Jeder Befund ist anhand von Zitat und Berechnungslauf ohne weitere Quellen nachvollziehbar.
- Wird ein Lauf mit denselben Eingaben wiederholt, ergibt er denselben Hash.

Gemessen wird das über die Evals (Precision und Recall je Feld), Ergebnis in `evals/results/latest.md`.
