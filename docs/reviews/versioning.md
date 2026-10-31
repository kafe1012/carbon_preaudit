# Review: Versionierung über Git-Tags

Geprüft: uncommittete Änderungen auf `chore/versioning` (`tools/local_tools/bump_script.py`,
`tools/pyproject.toml`, `tests/test_bump_script.py`, `.github/workflows/ci.yml`,
`.github/workflows/release.yml`, `pyproject.toml`, `uv.lock`, `Dockerfile`, `README.md`, `CLAUDE.md`,
`docs/adr/0006-versioning-via-git-tags.md`) · Grundlage: `CLAUDE.md`, ADR 0002, ADR 0005, ADR 0006

Selbst ausgeführt: `uv run ruff check .`, `uv run pyright` und `uv run pytest` sind grün (12 Tests).
In einer Kopie unter `/private/tmp/…/scratchpad` habe ich außerdem `uv version` und `git-changelog`
nachgestellt. `actions/checkout@v7` habe ich per `gh api` geprüft. Das Repo selbst ist unverändert.

## Kritisch

- [x] **K1** `tools/local_tools/bump_script.py:15,66`: Eine Dev-Version, die das Bump-Skript selbst
  geschrieben hat, besteht die eigene CI-Prüfung nicht. `_generate_version` erzeugt den SemVer-String
  `0.2.0-dev20261101000000`. `uv version` normalisiert ihn aber nach PEP 440 und schreibt
  `version = "0.2.0.dev20261101000000"` in `pyproject.toml`, also mit Punkt statt `-dev`. Nachgestellt:
  `uv version 0.2.0-dev20261101000000` → `carbon-preaudit 0.1.0 => 0.2.0.dev20261101000000`, und
  `uv version --short` liefert danach die Form mit Punkt. Im Job `version` (`ci.yml:42`) findet
  `partition("-dev")` dann kein `-dev`, und der ganze String wird als Basis mit
  `['1.0.0', '0.1.0', '0.0.1']` verglichen. Geprüft mit
  `uv run bump verify-version 0.2.0.dev20261101000000`: `Invalid version …`, Exit-Code 1. Das in README
  und CLAUDE.md dokumentierte `-d` führt also immer zu einem roten `version`-Job. Der Test
  `tests/test_bump_script.py:17,20` prüft nur die `-dev`-Form, die in `pyproject.toml` nie vorkommt,
  und bleibt deshalb grün. Dass ADR 0006 Zeile 18 „`-dev`-Suffix“ schreibt, ist ebenso ungenau, denn
  gespeichert wird PEP 440 (`.devN`), nicht SemVer. Vorschlag: In `is_version_valid` den Basisteil per
  `packaging.version.Version(current_version).base_version` bestimmen. `packaging` ist über dunamai
  schon im Lockfile. Damit sind beide Schreibweisen abgedeckt, und eine Dev-Version wird nur
  akzeptiert, wenn `.is_devrelease` gilt. Andere Pre-/Post-Release-Marker wie `rc1` oder `.post1`
  müssen dann ausdrücklich abgelehnt werden. Den Test um `0.2.0.dev20261101000000` ergänzen und die
  ADR-Formulierung anpassen.

  Erledigt: `is_version_valid` bestimmt die Basis per `packaging.version.Version(...).base_version` (explizite Abhängigkeit in `tools/pyproject.toml`), Basis exakt verglichen. `rc`, `.post`, lokale Marker und Epochen werden abgelehnt. `_generate_version` erzeugt die PEP-440-Form `X.Y.Z.devN`. ADR angepasst.
## Wichtig

- [x] **W1** `docs/adr/0006-versioning-via-git-tags.md:33-34`, `README.md:63-64`: Der Ablauf nach
  einem Release ist zwar benannt, aber widersprüchlich und für einige PRs nicht lösbar. Nach dem
  Release ist der Tag gleich der Version, deshalb ist der Job `version` auf **jedem** folgenden PR rot,
  bis ein Bump gemergt ist. Das betrifft auch Dependabot-PRs (`.github/dependabot.yml`, drei
  Ökosysteme, wöchentlich) und Agenten-PRs. Agenten dürfen laut `CLAUDE.md` die Version aber nur auf
  Anweisung setzen, und Dependabot kann es gar nicht. Das README beschreibt die umgekehrte Reihenfolge,
  nämlich zuerst den Bump „in einem eigenen PR“ und nach dem Merge das Release. Daraus folgt nicht,
  dass direkt nach jedem Release ein Bump-PR fällig ist. Vorschlag, eine Variante wählen und in ADR und
  README einheitlich beschreiben: (a) In CI zusätzlich `Version == letzter Tag` als gültig zulassen. Die
  strenge Prüfung „echter Nachfolger“ macht dann nur noch `release.yml:46-49`, wo sie auch hingehört.
  So blockiert nichts, und ein vergessener Bump fällt spätestens beim Release auf. Oder (b) die
  Blockade bewusst lassen und festschreiben, dass der Mensch direkt nach jedem Release den Bump-PR
  öffnet und dass Dependabot-PRs bis dahin rot sind.
  Erledigt: `verify-version` lässt Gleichstand zu, `verify-version --release` (Release-Workflow) verlangt einen echten Nachfolger. ADR 0006, README und CLAUDE.md angepasst.
- [ ] **W2** `.github/workflows/ci.yml:26-42`: `version` ist im Ruleset `protect-master` kein
  Required Check. Abgefragt mit `gh api repos/kafe1012/carbon_preaudit/rulesets/26157294`: Required
  sind nur `checks`, `docker` und `pr-title`. Die Aussage in ADR 0006 Zeile 34, sonst „schlägt der Job
  `version` fehl“, bleibt deshalb folgenlos: Ein PR mit falscher Version lässt sich trotzdem mergen.
  Vorschlag: Nach der Entscheidung zu W1 `version` als Required Check eintragen (bei Variante a
  unproblematisch) oder in ADR 0006 festhalten, dass der Job nur informiert.
  Offen: nicht umsetzbar durch den Implementierer (Ruleset). Nach erstem CI-Lauf, Hauptsession. ADR 0006 vermerkt den Stand.
- [x] **W3** `tests/test_bump_script.py:21,27,34`: Alle Tests ersetzen `_generate_version` durch
  einen Fake. Die eigentliche Logik bleibt damit ungetestet: Aufruf von dunamai mit
  `tag_branch=origin/master`, `strict=True` ohne Tag, Format der Dev-Version und deren Normalisierung
  durch uv. Genau deshalb ist K1 durchgerutscht. Vorschlag: ein Test mit `tmp_path`, `git init`, einem
  Commit, Tag `0.1.0` und `git update-ref refs/remotes/origin/master HEAD` (lokal, ohne Netzwerk). Er
  prüft `_generate_version` für alle drei Stufen samt `-d` und den Fall „kein Tag“ (erwarteter Fehler).

  Erledigt: Tests laufen gegen ein echtes lokales Git-Repo in `tmp_path` (`origin/master` per `update-ref`, kein Netzwerk): Nachfolger, PEP-440-Dev-Version, `0.0.10`, `--release`, kein Tag.
## Hinweis

- [x] **H1** `tools/local_tools/bump_script.py:42-47`: Bei `strict=True` endet ein Repo ohne
  passenden Tag oder ein Shallow-Clone in einem `RuntimeError`-Traceback aus dunamai („No tags
  available and fallbacks disabled by strict mode“ bzw. „Repository does not contain full history“).
  Dasselbe passiert, wenn der neueste erreichbare Tag nicht dem Muster entspricht, etwa ein von Hand
  gesetzter Tag `demo` (dann wegen `latest_tag=True`). Vorschlag: in `_generate_version` abfangen und
  als `ClickException` mit Hinweis ausgeben („`git fetch --tags origin`, Tag `X.Y.Z` auf master
  nötig“).
  Erledigt: `RuntimeError`/`ValueError` aus dunamai werden in `_latest_tag_version` zu einer `ClickException` mit Hinweis.
- [x] **H2** `tools/local_tools/bump_script.py:14,43-48`: Lokal liest das Skript den
  Remote-Tracking-Ref `origin/master`. Wer seit dem letzten Release nicht gefetcht hat, bekommt eine
  Version aus einem veralteten Tag vorgeschlagen, zum Beispiel erneut `0.1.0` statt `0.2.0`. Das fällt
  erst in CI auf. Vorschlag: In `main` vor `_generate_version` `git fetch --tags origin master`
  ausführen oder den Schritt im README nennen.
  Erledigt: `version` führt vorher `git fetch --tags origin master` aus, bei Fehlschlag Warnung und Weiterlaufen.
- [x] **H3** `.github/workflows/ci.yml:35,40-41` und `release.yml:26`: Bei `fetch-depth: 0` holt
  `actions/checkout@v7` bereits `+refs/heads/*:refs/remotes/origin/*` und alle Tags
  (`src/ref-helper.ts`, `getRefSpecForAllHistory`). `origin/master` ist also auch im PR-Checkout
  vorhanden. `fetch-tags` ist ein gültiger Input, hier aber wirkungslos, und der zusätzliche
  `git fetch --no-tags origin master` ist redundant. Beides schadet nicht. Der Kommentar „Safeguard“
  legt aber nahe, dass es ohne nicht ginge. Vorschlag: streichen oder den Kommentar korrigieren.
  Erledigt: `fetch-tags` und der zusätzliche `git fetch` in ci.yml, `fetch-tags` in release.yml entfernt.
- [x] **H4** `.github/workflows/release.yml:50-54`: `git-changelog --release-notes` liefert den
  **ersten** Versionsabschnitt der erzeugten Datei, siehe `get_release_notes` in git-changelog. Im
  Normalfall ist das der Abschnitt der neuen Version. In der Kopie nachgestellt mit einem Commit nach
  `0.0.0` bzw. `0.1.0`: Es kommen nur die Commits dieser Version, korrekt. Gibt es seit dem letzten Tag
  aber keinen Commit, erzeugt `--bump` keinen Abschnitt, und die Notes des **vorherigen** Tags landen
  im neuen Release. Genau so ist der Stand auf `0.0.0`: `git show 0.0.0:pyproject.toml` enthält bereits
  `version = "0.1.0"`. Vorschlag: nach Zeile 54 prüfen, dass die erste Zeile von `notes.md` mit
  `## [$VERSION]` beginnt, sonst abbrechen. Optional eine `concurrency`-Gruppe gegen doppelte Starts
  ergänzen.
  Erledigt: release.yml bricht ab, wenn `notes.md` nicht mit `## [$VERSION]` beginnt. `concurrency` nicht ergänzt (optional).
- [x] **H5** `docs/adr/0006-versioning-via-git-tags.md:9,37`: „Releases sollen … nicht von einem
  Agenten ausgelöst werden können“ wird nur organisatorisch umgesetzt. Technisch kann jeder mit
  Schreibrecht, also auch ein Agent mit `gh`, `gh workflow run release` starten oder einen Tag pushen.
  Ein Tag-Ruleset gibt es nicht, nur `protect-master` für Branches. Vorschlag: „können“ zu „dürfen“
  abschwächen oder ein Tag-Ruleset bzw. eine Environment-Freigabe für den Job `release` einrichten.
  Erledigt: ADR 0006 hält fest, dass Releases per Absprache gestartet werden und ein Tag-Ruleset später möglich ist. Nicht umgesetzt.
- [x] **H6** `CLAUDE.md:115-125`: Der Abschnitt „Struktur“ nennt das neue Top-Level-Verzeichnis
  `tools/` nicht, „Stack“ nennt weder dunamai, git-changelog noch click. Vorschlag: jeweils eine Zeile
  ergänzen, damit Agenten `tools/` nicht für Fremdcode halten.
  Erledigt: `tools/` unter Struktur, dunamai, git-changelog und click unter Stack in CLAUDE.md.
- [x] **H7** `README.md:54-64`: Der Abschnitt ist formal in Ordnung, ein Befehl pro Block. Der zweite
  Absatz beschreibt aber den Release-Prozess, und der steht schon in ADR 0006. Vorschlag: im README den
  Befehl und einen Verweis auf ADR 0006 lassen und den Ablauf nach der Entscheidung zu W1 nur in der
  ADR beschreiben.

  Erledigt: README-Abschnitt auf Befehl und Verweis auf ADR 0006 gekürzt.
## Fazit

Gerüst, Rechte (`contents: write`, `GH_TOKEN`), Checkout-Inputs und Release-Notes funktionieren auf
GitHub-Runnern wie beabsichtigt. Squash-Merges halten `master` linear, deshalb bleiben die Tags von
`origin/master` aus erreichbar. Nach Behebung von K1 und einer klaren Entscheidung zu W1/W2 ist der
Schritt abnahmefähig, W3 sollte mit K1 zusammen erledigt werden.
