# Review 02: Projektgerüst

Geprüft: uncommittete Änderungen auf `feat/02-scaffold` (`src/carbon_preaudit/web/app.py`,
`tests/test_health.py`, `Dockerfile`, `.dockerignore`, `.github/workflows/ci.yml`,
`.github/workflows/pr-title.yml`, `examples/project.geojson`, `examples/plots.csv`) ·
Grundlage: `docs/plans/01-architecture.md` (Abschnitt „02 Projektgerüst“), `CLAUDE.md`,
ADR 0004, ADR 0005

## Kritisch

- [x] **K1** `.github/workflows/ci.yml:17`: `astral-sh/setup-uv@v10` gibt es nicht. Seit v8.0.0
  veröffentlicht setup-uv keine Major- oder Minor-Tags mehr, nur noch unveränderliche Release-Tags
  (Release-Notes v8.0.0: „You won't be able to use `@v8` or `@v8.0` any longer“). Geprüft mit
  `gh api repos/astral-sh/setup-uv/git/matching-refs/tags/v10`: Es gibt nur `v10.0.0` … `v10.3.3`.
  Das letzte Major-Tag ist `v7`. Der Job `checks` bricht auf GitHub schon beim Auflösen der Action
  ab („Unable to resolve action“), und die DoD „CI grün auf GitHub“ ist so nicht erreichbar. Lokal
  fällt das nicht auf, weil pre-commit die Workflows nur als YAML prüft. Vorschlag: auf
  `astral-sh/setup-uv@v10.3.3` pinnen, besser auf den Commit-SHA mit Kommentar `# v10.3.3`.
  Dependabot (`github-actions`, ADR 0004) aktualisiert beide Schreibweisen.
  Erledigt: `setup-uv@v10.3.3` gepinnt; `actions/checkout@v7` und `amannn/action-semantic-pull-request@v6` existieren als Tags (per `gh api` geprüft).

## Wichtig

- [x] **W1** `.github/workflows/ci.yml:19`: `python-version-file` ist kein Input von setup-uv. Laut
  `action.yml` von v10.3.3 gibt es `python-version`, `version` und `version-file`, wobei
  `version-file` die **uv**-Version angibt, nicht die Python-Version. GitHub meldet nur die Warnung
  „Unexpected input(s)“ und ignoriert die Zeile. Dass trotzdem 3.15 verwendet wird, liegt allein
  daran, dass uv `.python-version` selbst liest. Vorschlag: die `with:`-Zeile streichen, denn uv
  liest `.python-version` ohnehin. Alternativ `python-version: "3.15"` setzen, das ist aber doppelt
  gepflegt.
  Erledigt: `python-version-file` entfernt, uv liest `.python-version` selbst; stattdessen `version: "0.13.6"` (uv-Version, passend zum Hook).
- [x] **W2** `.github/workflows/ci.yml:20-22`: Die Prüfung, ob `uv.lock` aktuell ist, lässt sich
  unbemerkt umgehen. `uv sync --frozen` prüft den Lockfile nicht gegen `pyproject.toml`. Der
  folgende `uv run pre-commit …` läuft ohne `--frozen`/`--locked` und **aktualisiert** einen
  veralteten `uv.lock`, bevor pre-commit startet. Der `uv-lock`-Hook findet danach nichts mehr zu
  ändern, und pre-commit meldet keine Änderung, weil es nur Änderungen durch Hooks erkennt. Ein PR
  mit geänderter `pyproject.toml` und altem `uv.lock` wäre damit grün. Vorschlag: `uv sync
  --all-groups --locked` und auf Job-Ebene `env: UV_LOCKED: "1"`, damit auch alle `uv run` den
  Lockfile nur prüfen.
  Erledigt: `uv sync --all-groups --locked` und `UV_LOCKED: "1"` auf Job-Ebene von `checks`.
- [x] **W3** `examples/project.geojson:2`: Die Datei ist ein `Feature` mit `properties`. Der Plan
  legt für `ProjectInputs.polygon` aber `type == "Polygon"` fest
  (`docs/plans/01-architecture.md:61`). Mit dieser Datei würde Schritt 03 die eigene Beispieldatei
  ablehnen, oder er müsste ungeplant Features auspacken. Vorschlag: nur das `geometry`-Objekt
  speichern (`{"type": "Polygon", "coordinates": …}`). Wenn der Name gebraucht wird, gehört er in
  den Dateinamen oder die README. Der Ring selbst ist in Ordnung: geschlossen, gegen den
  Uhrzeigersinn wie in RFC 7946 verlangt, Koordinaten in der Reihenfolge Länge, Breite.
  Erledigt: `examples/project.geojson` ist jetzt das reine Polygon-Objekt, Koordinaten unverändert.

## Hinweis

- [x] **H1** `Dockerfile:1` und `ci.yml:17`: Die uv-Version ist nirgends fest. Das Basis-Image
  `ghcr.io/astral-sh/uv:python3.15-trixie-slim` wandert mit jedem uv-Release, setup-uv installiert
  ohne `version` die neueste Version, und nur der `uv-lock`-Hook ist auf 0.13.6 gepinnt. Lokal, in
  CI und im Image können also drei verschiedene uv-Versionen laufen. Für ein Projekt mit dem
  Leitprinzip „Reproduzierbare Läufe“ ist das unschön, auch wenn der Hash davon nicht abhängt.
  Vorschlag: `[tool.uv] required-version = "==0.13.6"` in `pyproject.toml`, denn setup-uv liest es
  standardmäßig. Dazu ein versioniertes Image-Tag, z. B. `uv:0.13.6-python3.15-trixie-slim`. Damit
  Dependabot das Image weiter aktualisiert, kommt in `.github/dependabot.yml` das Ökosystem
  `docker` hinzu (wäre eine kleine Ergänzung zu ADR 0004).
  Erledigt: Dockerfile nutzt `uv:0.13.6-python3.15-trixie-slim` (per `podman pull` verifiziert), Dependabot-Ökosystem `docker` ergänzt; setup-uv mit `version: "0.13.6"`. Kein `required-version` (Vorgabe).
- [x] **H2** `tests/test_health.py:1`: `TestClient` braucht einen HTTP-Client. Im Lock kommt
  `httpx2` nur indirekt über `anthropic` herein (`uv.lock:30`), nicht über FastAPI, Starlette oder
  die Dev-Gruppe. Der Test hängt also implizit am Anthropic SDK. Vorschlag: den Client, den die
  installierte Starlette-Version für `TestClient` erwartet, explizit in die Dev-Gruppe aufnehmen.
  Erledigt: `httpx2` (von `starlette.testclient` importiert) per `uv add --dev` in die Dev-Gruppe aufgenommen.
- [x] **H3** `.github/workflows/ci.yml:24-29`: Der Job `docker` baut das Image nur und startet es
  nicht. Das erfüllt die DoD. Ein Smoke-Test in CI (`docker run -d -p 8000:8000 …`, dann
  `curl --retry 5 --retry-connrefused localhost:8000/health`) würde aber absichern, was bisher nur
  lokal mit podman geprüft wurde: dass der Nicht-Root-User die `.venv` lesen und uvicorn starten
  kann. Optional.
  Erledigt: Job `docker` taggt das Image, startet den Container im Hintergrund, prüft `/health` mit Retry-Schleife und stoppt ihn.
- [ ] **H4** Plan, DoD „Pflicht-Checks im Ruleset“: Das lässt sich nicht aus dem Repo prüfen. Die
  Check-Namen, die ins Ruleset gehören, sind die Job-Namen `checks`, `docker` und `pr-title`. Sie
  erscheinen erst nach dem ersten Lauf auf GitHub als auswählbar, also erst nach Behebung von K1.
  Offen: nach erstem CI-Lauf, Hauptsession.

Ohne Befund geprüft: pre-commit überspringt in CI `uv-sync` (Manifest-Stages
`post-checkout/post-merge/post-rewrite`) und `commitlint` (Stage `commit-msg`) und installiert
deren Umgebungen auch nicht. pyright findet die `.venv` über `venvPath`/`venv` in
`pyproject.toml`, nachdem `uv sync` sie im Arbeitsverzeichnis angelegt hat. Die Cache-Mounts im
Dockerfile laufen vor `USER app` noch als root, `/root/.cache/uv` passt also. Weil der Bytecode
schon kompiliert ist, braucht der App-User keine Schreibrechte. `pyproject.toml` hat kein
`readme`-Feld, und der Build braucht nichts, was `.dockerignore` ausschließt. Die Titelprüfung
mit den Standardtypen passt zu `@commitlint/config-conventional`, und `chore(deps): …` von
Dependabot geht durch. Beispieldaten: 10/11/9 Bäume, entspricht 250–275 Bäumen/ha, BHD 8–35 cm,
Höhe 6–22 m, ρ 0,42–0,75 g/cm³. Handrechnung mit der Chave-Formel und dem Default 0,6 für die
2 fehlenden Werte: Σ 10,03 tCO₂e auf 0,12 ha ≈ 83,6 tCO₂e/ha, also ≈ 8 364 tCO₂e brutto auf
100,019 ha. Das ist für eine junge tropische Aufforstung plausibel. Scope: nichts über Schritt 02
hinaus gebaut.

## Fazit

Das Gerüst ist schlank und hält den Scope ein. Auf GitHub würde die CI aber wegen K1 sofort
scheitern, und W2 lässt einen veralteten Lockfile durch. Nach Behebung von K1, W1 bis W3 und
einem grünen Lauf auf GitHub (samt Ruleset-Eintrag, H4) ist der Schritt abnahmefähig.
