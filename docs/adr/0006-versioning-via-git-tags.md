# ADR 0006: Versionierung über Git-Tags

Status: angenommen · Datum: 2026-10-31

## Kontext

Das Projekt braucht eine nachvollziehbare App-Version und Releases mit Notes. Eine Version, die von Hand in
`pyproject.toml` gepflegt wird, driftet leicht: Sie wird vergessen, doppelt vergeben oder springt. Die
Releases sollen außerdem nicht von einem Agenten ausgelöst werden.

## Entscheidung

- SemVer ohne `v`-Präfix, also `0.1.0`. Der Tag heißt wie die Version. Der erste Tag ist `0.0.0`.
- Die Version in `pyproject.toml` setzt nur ein Mensch per Bump-Skript (`uv run bump version …`, Paket
  `tools/`, uv-Workspace-Mitglied). Das Skript leitet den Vorschlag aus dem letzten Tag auf `origin/master` ab,
  mit `dunamai`. Das Ergebnis ist reproduzierbar.
- CI prüft im Job `version`, dass die Version in `pyproject.toml` ein gültiger Nachfolger des letzten Tags
  ist (nächste Major-, Minor- oder Patch-Version, optional als PEP-440-Dev-Version `X.Y.Z.devN`, so schreibt
  `uv version` sie) oder gleich dem letzten Tag ist. Andere Pre-/Post-Release-Marker gelten als ungültig.
- Ein Release ist ein manueller GitHub-Workflow `release` (`workflow_dispatch`, nur auf `master`). Er bricht
  bei Dev-Version, vorhandenem Tag oder einer Version ab, die kein echter Nachfolger ist
  (`bump verify-version --release`). Auch ohne Commit seit dem letzten Tag bricht er ab, weil dann die
  Release-Notes fehlen. Sonst erzeugt er mit `git-changelog` die
  Notes aus den Conventional Commits und legt per `gh release create` Tag und GitHub-Release an. Eine
  `CHANGELOG.md` gibt es im Repo nicht, die Notes entstehen nur für das Release.
- Es gibt keinen Image-Push. Ein Deployment liegt nicht im Scope.

## Abgrenzung zu `CALC_VERSION` und `PARAMS_VERSION`

`CALC_VERSION` und `PARAMS_VERSION` (ADR 0002) beschreiben die Berechnung und fließen in den Lauf-Hash ein.
Die App-Version beschreibt das Release als Ganzes, etwa Weboberfläche oder Doku. Sie gehört nicht in den
Hash: Ein Release ohne Änderung an Rechenlogik oder Parametern darf Ergebnisse und Hashes nicht verändern.

## Konsequenzen

- Nach einem Release ist der Tag gleich der Version in `pyproject.toml`. Der Job `version` lässt diesen
  Gleichstand zu, damit nachfolgende PRs (auch Dependabot und Agenten) nicht blockieren. Gebumpt wird erst
  vor dem nächsten Release, in einem eigenen PR. Ein vergessener Bump fällt spätestens im Release-Workflow
  auf, der einen echten Nachfolger verlangt.
- Der Job `version` ist Pflicht-Check im Ruleset `protect-master`. Ein PR mit ungültiger Version lässt sich
  nicht mergen.
- Der Job `version` braucht die komplette Historie samt Tags und `origin/master`.
- Die Gültigkeitsprüfung vergleicht den Basisteil exakt, `0.0.10` gilt also nicht als Nachfolger von `0.0.0`.
- Releases starten nur Menschen, per Absprache. Technisch kann jeder mit Schreibrecht den Workflow starten
  oder einen Tag pushen. Ein Tag-Ruleset oder eine Environment-Freigabe für den Job `release` ist später
  möglich. Agenten setzen die Version nur auf ausdrückliche Anweisung.
- Der Bump-Befehl holt vorher `git fetch --tags origin master` und warnt, wenn das scheitert. Fehlt ein
  passender Tag oder ist die Historie unvollständig, endet er mit einer klaren Fehlermeldung.
