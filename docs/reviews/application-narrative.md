# Review: Einordnung als Arbeitsprobe (application-narrative)

Geprüft: uncommittete Änderungen auf `docs/application-narrative` gegen `master` (8be6e6d): `docs/overview.md`,
`docs/adr/0009-operations-and-scaling-path.md` (neu), `README.md`, `CLAUDE.md`, `DOMAIN.md`,
`docs/problem-statement.md`, ADR 0003, ADR 0007; zum Vergleich alle übrigen `.md` im Repo, darunter `WEEKEND-PLAN.md` ·
Grundlage: `CLAUDE.md`, ADR 0001–0009, `audit/summary.md`, PR #10, Code in `Dockerfile`, `.github/workflows/`,
`web/app.py`, `web/static/app.js`, `preaudit/extractor.py`

ruff, pyright und pytest (261 Tests) sind grün.

Ohne Befund geprüft: Alle relativen Links und Anker in den geprüften `.md` lösen auf (per Skript geprüft).
Es gibt keine Firmen- oder Personennamen; `kafe1012` steht nur in der Clone-URL der README, wie schon vorher.
Die README bleibt Setup und verweist nur. Stimmig mit dem Code sind die Aussagen zu CI-Jobs, Smoke-Test,
Container ohne Root-Rechte, Layer-Caching, `.dockerignore`, Release ohne Image-Push, Umgebungsvariablen im Extractor,
`_LazyExtractor`, pyright strict für `src`, `tools` und `evals`, 12 Eval-Fällen, SRI-Hashes der CDN-Skripte
sowie den Audit-Zahlen (33 Findings, 3 offen, F-32).

## Kritisch

- [x] **K1** `docs/overview.md:92-93`: „Die Darstellung im Browser ist nur über den TestClient geprüft“ ist falsch.
  Schritt 07 wurde im Browser mit echtem Gemini geprüft. Dabei fiel ein Fehler auf: Ab der zweiten Prüfung blieb die
  Karte leer. Behoben ist er in `src/carbon_preaudit/web/static/app.js:28-32` (`htmx:afterSettle`), belegt in der
  PR-Beschreibung von #10. Der verlinkte Anker `audit/summary.md#nicht-verifiziert` belegt nur etwas Engeres: F-11,
  also die Darstellung der Fehlermeldungen (`audit/summary.md:115`). Der Satz unterschätzt genau den Leitsatz 2.
  Vorschlag: „Im Browser manuell mit echtem Gemini geprüft ([PR #10](https://github.com/kafe1012/carbon_preaudit/pull/10)).
  Dabei wurde eine leere Karte ab der zweiten Prüfung gefunden und behoben (app.js). Automatisierte Browser-Tests gibt
  es nicht, und die Darstellung der Fehlermeldungen ist nur über den TestClient geprüft (Audit F-11).“
  Erledigt: Satz ersetzt: manuelle Browser-Prüfung mit echtem Gemini (PR #10), leere Karte gefunden und behoben, keine automatisierten Browser-Tests, F-11 für Fehlermeldungen. Audit-Link entfernt.

## Wichtig

- [x] **W1** `docs/overview.md:14`: Leitsatz 3 nennt „zuverlässige Server-Infrastruktur und Build-Pipeline“. Laut
  Abschnitt „DevOps und Betrieb“ (Z. 52-65) und ADR 0009 ist aber nur die Build-Pipeline bis zum geprüften Container
  vorhanden, eine Server-Infrastruktur gibt es nicht. Als Überschrift klingt der Satz gebaut. Vorschlag: den Leitsatz
  belassen und im Abschnitt einen Satz voranstellen, etwa „Die Build-Pipeline ist gebaut, die Server-Infrastruktur ist
  als Pfad beschrieben“.
  Erledigt: Satz am Anfang von „DevOps und Betrieb“: Build-Pipeline bis zum Container gebaut, Server-Infrastruktur als Pfad in ADR 0009. Leitsatz 3 unverändert.
- [x] **W2** `docs/adr/0009-operations-and-scaling-path.md:25-26`: Laut ADR „taugt `/health` als Liveness- und
  Readiness-Probe“. `/health` antwortet aber immer mit `ok` (`web/app.py:120-123`), auch ohne API-Key. Eine
  Readiness-Probe würde also einen Pod freigeben, der keine Prüfung liefert (F-32, Z. 61 derselben ADR). Vorschlag:
  „taugt als Liveness-Probe; eine Readiness-Probe müsste zusätzlich prüfen, ob der Extractor konfiguriert ist“.
  Erledigt: ADR 0009: `/health` nur Liveness; Readiness-Prüfung der Konfiguration unter „Was der Pfad bräuchte“ ergänzt.
- [x] **W3** `WEEKEND-PLAN.md`: Die Datei liegt versioniert im Wurzelverzeichnis, ist unverändert und widerspricht der
  neuen Erzählung. Z. 114-118 verlangt eine README mit Problem, Mermaid-Architektur, Eval-Ergebnis und „So wurde
  gebaut“. Das widerspricht der Regel „README nur Setup“ und überschneidet sich mit `docs/overview.md`. Z. 16 setzt
  `ANTHROPIC_API_KEY`, obwohl Gemini der Default ist (ADR 0008). Die Tabelle in Z. 124-133 konkurriert mit dem
  Überblick. Vorschlag: oben den Hinweis „Ursprünglicher Wochenendplan, historisch; aktueller Stand in
  docs/overview.md“ ergänzen oder die Datei nach `docs/plans/` verschieben.
  Erledigt: Hinweis am Anfang von `WEEKEND-PLAN.md` (historisch, Verweis auf Überblick, Plan 01 und ADR 0008), Rest unverändert, Datei bleibt am Ort.
- [x] **W4** `docs/overview.md:93-94`: „bewusst schlicht und ausreichend, nicht das Kernstück“ nimmt Leitsatz 2
  („pragmatisch und solide“) zurück. Belege für „solide“ stehen im selben Absatz: Eingabegrenzen, lesbare Fehler,
  SRI, getestetes Highlighting und die Browser-Prüfung aus K1. Vorschlag: „pragmatisch und bewusst schlicht: kein
  Build-Schritt, kein Framework“ und „nicht das Kernstück“ streichen.
  Erledigt: Ersetzt durch „pragmatisch und bewusst schlicht: kein Build-Schritt, kein Framework“, mit KI gebaut, nicht Hauptspezialisierung.
- [x] **W5** `docs/overview.md:3-6, 110-118`: Die Domänen-Einordnung ist dem Menschen besonders wichtig, steht aber
  erst im vorletzten Abschnitt. Dieser beginnt außerdem mit „an einer echten Fachdomäne ausgerichtet“. Die
  Einleitung sagt dazu nichts. Der Kernsatz „entsteht nicht an einem Wochenende“ steht zudem doppelt, in Z. 117 und
  in `DOMAIN.md:8-9`. Vorschlag: In die Einleitung einen Satz aufnehmen, etwa „Fachlich ist es ein stark vereinfachtes
  Beispiel; echtes Domänenwissen muss aufgebaut werden, siehe [Einordnung](../DOMAIN.md#einordnung)“. Im Abschnitt
  „Domäne“ dann nur noch verlinken statt wiederholen.
  Erledigt: Einleitung enthält jetzt den Satz zur Domänen-Einordnung; Abschnitt „Domäne“ verweist nur noch auf `DOMAIN.md#einordnung`.

## Hinweis

- [x] **H1** `docs/overview.md:47-48`: Laut Text laufen „dieselben Prüfungen in CI“. commitlint läuft aber nur in der
  Stufe `commit-msg` (`.pre-commit-config.yaml:35-41`) und damit nicht bei `pre-commit run --all-files`
  (`ci.yml:23`). In CI prüft stattdessen `pr-title.yml` den PR-Titel. Vorschlag: „in CI laufen dieselben Hooks,
  statt commitlint prüft dort pr-title.yml den PR-Titel“.
  Erledigt: commitlint lokal, in CI die übrigen Hooks und `pr-title.yml` für den PR-Titel.
- [x] **H2** `docs/overview.md:46`: Der verlinkte Eval-Bericht stammt von Commit `a057e3c`
  (`evals/results/latest.md:11`), also aus der Zeit vor den Audit-Korrekturen. Laut `audit/summary.md:113` steht ein
  Eval-Lauf mit Key nach F-20 noch aus. Vorschlag: den Stand am Link vermerken.
  Erledigt: Link zum Bericht um „Lauf vor den Audit-Korrekturen, Audit F-15“ ergänzt.
- [x] **H3** `docs/overview.md:30`: „Der Webprozess hält keinen Zustand“ ist ungenauer als
  `docs/adr/0009-operations-and-scaling-path.md:28-31`. Dort steht, dass der Prozess den Extractor-Client im
  Speicher hält und nur keine Ergebnisse speichert. Vorschlag: „speichert keine Ergebnisse“.
  Erledigt: Angeglichen: „speichert keine Ergebnisse“.
- [x] **H4** `docs/overview.md:10-11`: Leitsatz 1 sagt „schnell skalieren kann“, Z. 4 dagegen „skalieren könnte“
  und ADR 0009 Z. 57 „Einschätzung, keine Messung“. Vorschlag: einheitlich „könnte“ oder den Leitsatz als allgemeine
  Aussage kennzeichnen, deren Beleg die Struktur ist und keine Messung.
  Erledigt: Leitsatz 1: „darauf ausgelegt, schnell zu skalieren“, Beleg ist die Struktur, keine Messung.

## Fazit

Die Botschaft ist über README, DOMAIN, Problem Statement, CLAUDE.md und die ADRs stimmig, und alle Links lösen auf.
Angedeutetes ist bis auf W1 und W2 klar als Pfad markiert. Nach Korrektur von K1 und mit W1 bis W5 trägt die Doku die
drei Leitsätze und die Domänen-Einordnung ohne Übertreibung und ohne unnötige Untertreibung.
