# ADR 0009: Betriebs- und Skalierungspfad, beschrieben statt umgesetzt

Status: angenommen · Datum: 2026-11-01

## Kontext

Das Repo ist eine Arbeitsprobe vom Wochenende und kein Produkt. Es soll zeigen, dass die Codebasis auf einen
Betrieb bei einem Hyperscaler vorbereitet ist, ohne diesen Betrieb zu bauen. Ohne Entscheidung wäre unklar, ob
Helm, Terraform oder eine gehostete Datenbank vergessen wurden oder bewusst fehlen.

## Entscheidung

Der Pfad wird hier beschrieben und nicht umgesetzt. Im Repo gibt es dafür weder Chart noch Terraform-Code noch
eine Datenbank. Zielbild: [Diagramm in docs/overview.md](../overview.md#devops-und-betrieb).

### Schon vorbereitet

- **Konfiguration über die Umgebung:** Anbieter, Modell und API-Keys kommen aus Umgebungsvariablen
  (`CARBON_PREAUDIT_PROVIDER`, `CARBON_PREAUDIT_MODEL`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`), siehe
  [extractor.py](../../src/carbon_preaudit/preaudit/extractor.py) und [.env.example](../../.env.example).
  Keys liegen nicht im Image ([.dockerignore](../../.dockerignore)). Host und Port stehen dagegen fest im
  `CMD` des [Dockerfile](../../Dockerfile).
- **Container ohne Root-Rechte:** Das [Dockerfile](../../Dockerfile) legt einen Systembenutzer an und wechselt
  mit `USER app` dorthin.
- **Health-Endpunkt:** `/health` in [app.py](../../src/carbon_preaudit/web/app.py) taugt als Liveness-Probe, er
  antwortet immer mit `ok`. Die CI nutzt ihn bereits als Smoke-Test im Job `docker` ([ci.yml](../../.github/workflows/ci.yml)).
  Das Dockerfile enthält kein `HEALTHCHECK`. Als Readiness-Probe taugt er nicht, siehe unten.
- **Zustandsloser Webprozess:** Der Webprozess schreibt nichts: Ein Lauf wird je Anfrage berechnet und nicht
  gespeichert. Gehalten wird nur der Extractor-Client im Speicher (`_LazyExtractor` in
  [app.py](../../src/carbon_preaudit/web/app.py)). Mehrere Instanzen sind damit möglich, es gibt aber auch
  keine Ablage der Ergebnisse.
- **Versionierte Releases über Git-Tags:** [ADR 0006](0006-versioning-via-git-tags.md),
  [release.yml](../../.github/workflows/release.yml). Der Workflow legt Tag und GitHub-Release an und pusht
  kein Image.
- **Reine Rechenlogik ohne I/O:** [calc/](../../src/carbon_preaudit/calc/) und
  [compare.py](../../src/carbon_preaudit/preaudit/compare.py) kennen weder Server noch Datenbank noch Netz.
- **Persistenzpfad:** [ADR 0003](0003-sqlite-instead-of-postgres.md) beschreibt SQLite hinter SQLAlchemy mit
  einem späteren Wechsel zu Postgres. Das ist nur Entwurf: `store/` und die Abhängigkeit fehlen, Plan-Schritt 04
  ist zurückgestellt ([Plan 01](../plans/01-architecture.md)).

### Was der Pfad bräuchte

- **Helm-Chart** für Deployment, Service, Probes (Liveness auf `/health`), Konfiguration über Umgebung und Secrets.
- **Terraform-Module** für Netz, Kubernetes-Cluster, Registry, Datenbank und Secret-Manager beim gewählten
  Hyperscaler (AWS, Azure oder GCP).
- **Readiness-Prüfung:** Ein Endpunkt, der die Konfiguration prüft, etwa ob ein API-Key gesetzt ist. Sonst
  gäbe eine Readiness-Probe einen Pod frei, der keine Prüfung liefert (Audit F-32).
- **Managed Postgres mit PostGIS** statt SQLite: RDS, Azure Database for PostgreSQL oder Cloud SQL. Das setzt
  das Persistenzmodul aus Schritt 04 voraus und betrifft laut ADR 0003 `store/` und die Verbindungs-URL.
- **Secrets aus dem Secret-Manager** statt `.env`, per Umgebungsvariable in den Pod gereicht.
- **Image-Push in eine Registry** als zusätzlicher Schritt im Release-Workflow, mit dem Git-Tag als Image-Tag.
- **Observability:** strukturierte Logs, Metriken und Traces, dazu Limits und Zugriffsschutz vor dem Dienst. Beides
  fehlt heute, auch Login und Begrenzung (siehe [README](../../README.md#im-container-starten)).

## Konsequenzen

- Nichts davon liegt im Repo. Das ist Absicht: Es ist eine Arbeitsprobe, und ungetesteter Infrastrukturcode
  wäre Schein.
- Die Aussage „könnte skalieren“ ist eine Einschätzung der Struktur, keine Messung. Last, Kosten und
  Betriebssicherheit sind nicht untersucht.
- Wer den Pfad geht, braucht je einen Plan-Schritt und eine eigene ADR für die Wahl des Hyperscalers und
  für die Datenbank.
- Der Container-Start nach README liefert ohne API-Key keine Prüfung (Audit F-32,
  [audit/summary.md](../../audit/summary.md)). Das ist vor einem Betrieb zu klären.
