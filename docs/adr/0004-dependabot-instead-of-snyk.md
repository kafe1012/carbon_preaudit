# ADR 0004: Dependabot statt Snyk

Status: angenommen · Datum: 2026-10-29

## Kontext

Die Abhängigkeiten (FastAPI, Pydantic, Anthropic SDK, pyproj, SQLAlchemy u. a.) sollen auf bekannte
Sicherheitslücken überwacht und aktuell gehalten werden. Zur Wahl stehen Snyk und Dependabot.

Snyk braucht ein eigenes Konto und einen `SNYK_TOKEN` als Repository-Secret. Ob Snyk `uv.lock` direkt
auswertet, ist nicht geprüft; vermutlich wäre ein Export nach `requirements.txt` in der Pipeline nötig.
Dependabot ist in GitHub eingebaut, kennt das Ökosystem `uv` und braucht weder Konto noch Token.

## Entscheidung

- Dependabot mit `.github/dependabot.yml` für `uv` und `github-actions`, wöchentlich. Minor- und
  Patch-Updates der Python-Abhängigkeiten werden zu einem PR gebündelt.
- Commit-Nachrichten der Dependabot-PRs beginnen mit `chore(deps)` und erfüllen damit Conventional Commits.
- Kein Snyk.

## Konsequenzen

- Kein zusätzliches Konto, kein Secret, keine weitere Pipeline-Stufe.
- Dependabot meldet bekannte Lücken in Abhängigkeiten, prüft aber keinen eigenen Code (kein SAST) und
  keine Container-Images.
- Snyk würde zusätzlich Code-Analyse, Container-Scans und eine Lizenzprüfung bringen. Es lässt sich
  später als eigener Job in GitHub Actions ergänzen (`snyk/actions`, `SNYK_TOKEN` als Secret), ohne
  den bestehenden Aufbau zu ändern.
- Die Hook-Versionen in `.pre-commit-config.yaml` aktualisiert Dependabot nicht. Dafür gibt es
  `uv run pre-commit autoupdate`.
