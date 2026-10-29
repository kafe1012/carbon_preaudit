# ADR 0005: Kurzlebige Branches und Squash-Merge

Status: angenommen · Datum: 2026-10-29

## Kontext

Die Historie soll den Ablauf Planen → Umsetzen → Prüfen → Review → Ausbessern nachvollziehbar zeigen, mit
genau einem Commit pro Plan-Schritt. Auf einem Branch entstehen aber mehrere Commits: Umsetzung, Fixes aus
dem Review, Lint. Lokal sichern pre-commit und commitlint saubere Commits ab, lassen sich aber mit
`--no-verify` umgehen. Ein direkter Push auf `master` würde Checks und Review überspringen.

## Entscheidung

- Trunk-based: `master` ist immer grün. Jeder Plan-Schritt läuft auf einem kurzlebigen Branch
  (`feat/03-calculation`, `docs/…`, `chore/…`) und kommt per PR zurück.
- Erlaubt ist nur Squash-Merge. Der PR-Titel wird zur Commit-Nachricht auf `master` und muss eine
  Conventional-Commit-Nachricht sein. Gemergte Branches werden automatisch gelöscht.
- Ein Ruleset auf `master` verlangt einen PR, eine lineare Historie und sperrt Force-Push und Löschen.
  Ab Schritt 02 kommen die CI-Jobs als Pflicht-Checks dazu, ebenso eine Prüfung des PR-Titels.
- Reviewt wird lokal: Der `reviewer`-Agent schreibt `docs/reviews/NN-<thema>.md`, und der PR verlinkt
  die Datei. Einen PR-Agenten in CI gibt es nicht.

## Konsequenzen

- `master` zeigt einen Commit pro Schritt. Die Zwischenstände bleiben im PR sichtbar.
- Saubere Commits sind dreifach abgesichert: lokal durch pre-commit und commitlint, in CI durch die
  Checks und die Titel-Prüfung, auf GitHub durch das Ruleset.
- Das Ruleset setzt GitHub Free nur bei öffentlichen Repos durch. Deshalb ist das Repo öffentlich.
- Ein PR-Agent in CI, etwa `anthropics/claude-code-action`, ließe sich später ergänzen. Er bräuchte
  `ANTHROPIC_API_KEY` als Secret und kostet pro Lauf. Das lokale Review bleibt als Datei im Repo und
  ist damit besser nachvollziehbar.
- Pro Schritt kommt etwas Aufwand dazu: Branch anlegen, PR öffnen, mergen.
