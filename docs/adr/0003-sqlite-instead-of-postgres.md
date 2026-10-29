# ADR 0003: SQLite statt Postgres für die Demo

Status: angenommen · Datum: 2026-10-29

## Kontext

Berechnungsläufe sollen gespeichert werden, damit ein Lauf über seinen Hash wieder abrufbar ist. Die Demo
läuft lokal und in einem einzelnen Docker-Container, ohne Mandanten, ohne Login und mit einem Nutzer.
Geodaten werden nur angezeigt, nicht abgefragt. Ein eigener Datenbankserver bringt Setup, Docker Compose
und Testinfrastruktur mit, die für diesen Umfang nichts beitragen.

## Entscheidung

- Persistenz mit SQLAlchemy 2 auf SQLite: eine Datei im Betrieb, `sqlite://` im Speicher für Tests.
- Eine Tabelle `runs` mit `run_hash` als Primärschlüssel, kanonischen Eingaben und Ergebnis als JSON sowie
  `created_at`.
- Nur Standard-SQLAlchemy ohne SQLite-spezifische Funktionen, damit ein Wechsel ohne Umbau des Modells möglich bleibt.
- Das Polygon wird als GeoJSON-Text gespeichert, nicht als Geometrie-Typ.

## Konsequenzen

- Kein zusätzlicher Dienst. `docker run` und `uv run pytest` reichen aus.
- Tests laufen schnell und isoliert gegen eine In-Memory-Datenbank.
- SQLite verträgt kaum gleichzeitige Schreibzugriffe und bietet keine räumlichen Abfragen.
- Postgres mit PostGIS wird sinnvoll, sobald Mandanten, mehrere schreibende Instanzen oder räumliche Abfragen
  (Plots im Polygon, Überlappung von Projekten) gebraucht werden. Der Wechsel betrifft dann `store/` und die
  Verbindungs-URL, nicht `calc/` oder `preaudit/`.
