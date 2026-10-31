# Fehlerkategorien K1–K12

Suchmuster sind Startpunkte für die Suche, keine Belege. Jeder Treffer wird im Kontext gelesen und bewertet.

## K1 – Verschluckte Fehler und stille Fallbacks
- Leere oder nur loggende Fehlerbehandlung: `except: pass`, `except Exception`, `catch (e) {}`, `.catch(() => {})`
- Stille Defaults bei Fehlern: `return []`, `return None`, `|| []`, `?? default`, `.get(key, default)` an Stellen, wo der Wert Pflicht ist
- Ungefragte „graceful degradation“, mehrere alternative Codepfade für denselben Zweck
- Leitfrage: Würde ein Fehler hier sichtbar werden, oder läuft der Code mit falschen Daten weiter?

## K2 – Symptome statt Ursachen
- Typ-Unterdrückung: `as any`, `# type: ignore`, `@ts-ignore`, `@ts-expect-error`, `eslint-disable`, `noqa`
- Timing-Workarounds: `sleep(`, `setTimeout` als Synchronisation, Retry-Schleifen ohne erkennbaren Grund
- Abgeschaltete Prüfungen: `verify=False`, `rejectUnauthorized: false`, deaktivierte Validierung
- Leitfrage: Welches eigentliche Problem wird hier verdeckt?

## K3 – Reward Hacking und schwache Tests
- Übersprungene Tests: `skip`, `xit`, `it.skip`, `@pytest.mark.skip`, `xfail` ohne Begründung
- Schwache Assertions: `assert True`, `assert result is not None`, nur Typ- statt Wertprüfung
- Hardcodierte Sonderfälle im Produktivcode für konkrete Testeingaben
- Über-Mocking: Der Test prüft nur noch den Mock, nicht das System
- Spiegeltests: erwartete Werte aus der Implementierung abgeleitet statt aus der Spezifikation
- Masse ohne Wert: viele nahezu identische Tests, die dasselbe prüfen

## K4 – Scope Creep (über die Git-Historie)
- Commits, die neben dem eigentlichen Zweck unzusammenhängende Dateien ändern
- Massen-Umformatierungen oder Umbenennungen, gemischt mit funktionalen Änderungen
- Commit-Message und Diff passen nicht zusammen

## K5 – Over-Engineering
- Interfaces oder abstrakte Klassen mit genau einer Implementierung
- Factories, Registries, Plugin-Systeme ohne zweiten Anwendungsfall
- Konfigurationsoptionen, die nirgends gesetzt oder gelesen werden

## K6 – Duplikation statt Wiederverwendung
- Mehrere Funktionen mit gleicher oder fast gleicher Logik
- Doppelte Konstanten, Helper, Utility-Module
- Abweichende Konventionen für dasselbe Problem (Naming, Fehlerbehandlung, Logging)

## K7 – Halluzinierte oder veraltete APIs und Packages
- Jede Dependency: Existiert sie in der Registry unter exakt diesem Namen? Wird sie tatsächlich importiert?
- Imports oder Methodenaufrufe, die in der installierten Version nicht existieren
- Deprecated APIs (Deprecation-Warnings im Testlauf, Changelogs der verwendeten Versionen)
- Plattformspezifisch, z. B. ServiceNow Scoped App: `gs.log`, `gs.print`, `Packages.*`, andere Global-only-APIs, nicht existierende GlideRecord-Methoden

## K8 – Unbelegte Erfolgsbehauptungen
- README, Docstrings, Kommentare oder Changelog beschreiben Features, die im Code fehlen oder nicht funktionieren
- Commit-Messages wie „fixed“ oder „works now“ ohne passende Änderung
- Dokumentierte Tests oder Coverage, die es nicht gibt

## K9 – Unvollständige Implementierungen
- `TODO`, `FIXME`, `XXX`, `NotImplementedError`, leere Funktionskörper, `pass` als einzige Anweisung
- Platzhaltertexte („rest of the logic here“, „implement later“)
- Mock-, Fake- oder Beispieldaten im Produktivpfad

## K10 – Spuren von Kontextverlust
- In der Git-Historie: Fixes, die später unbeabsichtigt rückgängig gemacht wurden; Hin-und-her-Änderungen an derselben Stelle
- Widersprüchliche Implementierungen derselben Regel an verschiedenen Stellen

## K11 – Security, Performance, Edge Cases
- Security: fehlende Input-Validierung an Systemgrenzen, String-Konkatenation in Queries, fehlendes Escaping (XSS), Log-Injection, hardcodierte Secrets, zu breite Berechtigungen, `CORS: *`
- Performance: N+1-Abfragen, Queries in Schleifen (z. B. GlideRecord in Loops), unnötiges Laden ganzer Datenmengen
- Edge Cases: Zeitzonen, Encoding, leere Mengen, `null`/`None`, Nebenläufigkeit
- Secrets nie ins Finding kopieren, nur den Fundort nennen.

## K12 – Unnötige Dependencies und Kommentar-Rauschen
- Libraries für triviale Logik oder ohne Verwendung
- Kommentare, die das Offensichtliche wiederholen oder Änderungshistorie statt Begründung enthalten
