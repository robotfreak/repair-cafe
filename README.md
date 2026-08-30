# Repair-Café Assistent

Lokaler KI-Assistent für Repair-Cafés auf dem Raspberry Pi 500: Laufzettel-Verwaltung,
Reparatur-Tagebuch mit Volltextsuche, Dokumenten-/Datenblatt-Verwaltung und ein
Reparatur-Assistent (lokal per ollama/phi4-mini — keine Cloud, DSGVO-freundlich).

**Alle Daten bleiben auf dem Pi.** Es gibt keine externe API, keinen API-Key, keine Cloud-Anbindung.

## Quick Start

```bash
# Service läuft automatisch (systemd):
systemctl status repair-cafe

# Web-UI im Browser (z.B. vom Tablet im WLAN):
#   http://<pi-ip>:5002
```

Manuell (für Entwicklung):

```bash
cd ~/repair-cafe
.venv/bin/python run.py        # Port 5002
.venv/bin/python -m pytest tests/ -v
```

## Funktionen

| Funktion | Beschreibung |
|---|---|
| **Laufzettel-Board** | Spalten: Offen / In Arbeit / Erledigt heute / Abzuholen. Statusmaschine mit geschützten Übergängen und Zeitstempeln. |
| **Haftungsausschluss** | Pflicht vor jeder Ticket-Anlage: Text (versioniert), Checkbox, **Unterschrift per Finger/Stift (Canvas)**, Print-Name. Signatur wird als PNG gespeichert (`data/signatures/`). |
| **Reparatur-Tagebuch** | Typisierte Einträge pro Ticket (notiz, diagnose, schritt, ersatzteil, ergebnis) — **nachträglich korrigierbar und löschbar** (Bearbeitung wird mit „(bearbeitet)", Zeitstempel und Bearbeiter markiert; Original-Autor bleibt). FTS5-Volltextsuche folgt Korrekturen sofort (Trigger auf INSERT/UPDATE/DELETE). |
| **Suche** | Ein Suchfeld über Tagebuch **und** Dokumente (bm25-Ranking). |
| **Dokumente** | PDF/Foto-Upload (max 20 MB) mit automatischer PDF-Textextraktion (pypdf); oder nur URL hinterlegen und serverseitig herunterladen. Identische Datei wird am selben Laufzettel/Gerät abgelehnt (409); jedes Dokument ist löschbar (DB + Datei). |
| **KI-Assistent** | Pro Ticket ein Chat: sammelt automatisch Gerät, Fehler, Tagebuch, Treffer aus früheren Reparaturen und Manual-Ausschnitte als Kontext und antwortet strukturiert (Ursachen → Prüfschritte → Ersatzteile → Sicherheit). Läuft 100% lokal. |
| **VDE/DGUV-Prüfung (optional)** | Geräte tragen eine Schutzklasse (SK I/II/III, optional Heizleistung kW). Am Laufzettel erscheint je Schutzklasse eine Checkliste nach **DIN VDE 0701-0702** mit Grenzwerten (Schutzleiter ≤ 0,3 Ω, Isolation ≥ 1/2/0,25 MΩ, Heizgeräte-Regeln 1 mA/kW max. 10 mA, Berührungsstrom ≤ 0,5 mA); Messwerte werden serverseitig bewertet (bestanden/nicht bestanden) und als Prüfprotokoll mitgedruckt. **Die Prüfung ist freiwillig** — keine Pflicht für die Rückgabe; Messmittel sind derzeit nicht vorhanden. |
| **Druckansicht** | Ticket-Ansicht → **Laufzettel** (A5-quer) mit Ankreuzfeldern + kompaktem VDE-Prüfblock, oder **separates VDE-Messprotokoll** (A4-hoch: Kopfdaten, Messgrößen-/Grenzwert-Tabelle, Gesamturteil, Unterschriftszeilen). Ohne gespeicherte Prüfung wird das Protokoll als **Blanko-Formular** zum handschriftlichen Ausfüllen gedruckt. |

## Architektur

```
Tablet (Browser, ein Gerät)
   │  http://pi:5002
   ▼
Flask (systemd: repair-cafe.service)  ──►  SQLite data/repair.db (WAL, FTS5)
   │                                        data/documents/  data/signatures/
   └──► ollama (localhost:11434, phi4-mini, ~4 tok/s warm)
```

- **Backend:** Python 3.11 (`.venv`), Flask-Blueprints pro Domain (`app/devices.py`, `app/tickets.py`, `app/journal.py`, `app/search.py`, `app/documents.py`, `app/waivers.py`, `app/assistant.py`), Kontext-Builder (`app/context_builder.py`) als reine, testbare Funktion.
- **Frontend:** Vanilla JS Einseiten-App (`static/app.js`, Hash-Routing), kein Framework, kein Build-Schritt.
- **Tests:** 164 pytest-Tests (TDD-entwickelt). ollama wird in Tests immer gemockt.

## Betrieb

- **Service:** `repair-cafe.service` (User pi, Restart on failure, enabled). Nach Code-Änderungen: `sudo systemctl restart repair-cafe`.
- **Backup:** täglich 20:00 via cron → `~/repair-backups/` (DB via Python sqlite3-Online-Backup, WAL-sicher + ZIP aller Signaturen/Dokumente, 30 Tage Retention). Manuell: `.venv/bin/python scripts/backup.py`. **Offsite-Kopie empfohlen** (z.B. USB-Stick oder rsync ins Vereinsnetz) — Unterschriften sind rechtlich relevante Anlagen.
- **Log:** `journalctl -u repair-cafe -f`

### Wiederherstellung aus Backup

```bash
sudo systemctl stop repair-cafe
# DB zurückspielen (WAL/SHM-Dateien vorher entfernen):
rm -f data/repair.db-wal data/repair.db-shm
cp ~/repair-backups/repair-YYYY-MM-DD.db data/repair.db
# Datei-Anhänge zurückspielen (Zip enthält signatures/ + documents/):
cd data && unzip -o ~/repair-backups/repair-files-YYYY-MM-DD.zip && cd ..
sudo systemctl start repair-cafe
curl -s http://localhost:5002/api/health   # → {"ok": true}
```

DB und Zip gehören zum selben Tagesstempel (`repair-YYYY-MM-DD.db` +
`repair-files-YYYY-MM-DD.zip`) — immer **beide zusammen** wiederherstellen:
Unterschriften ohne passende DB-Einträge (und umgekehrt) sind wertlos.

### Troubleshooting

| Symptom | Ursache / Lösung |
|---|---|
| UI nicht erreichbar | `systemctl status repair-cafe` — falls failed: `journalctl -u repair-cafe -n 50`. Port belegt? `ss -tlnp \| grep 5002`. |
| Assistent antwortet nicht | Läuft ollama? `systemctl status ollama` und `ollama list` (phi4-mini muss gelistet sein). Nach längerer Leerlaufzeit lädt das Modell 1–2 Min. in den RAM — erste Antwort dauert dann länger. |
| VDE-Prüfung fehlt am Laufzettel | Das Gerät hat keine Schutzklasse. Im Geräte-Tab aufklappen, Schutzklasse setzen (SK I/II/III) — danach erscheint die Prüfung (freiwillig) am Ticket. |
| Assistent sehr langsam | Normal auf dem Pi (2–4 tok/s → 60–220 s pro Antwort, siehe Abschnitt unten). Deutlich länger → Pi-Last prüfen (`top`), andere ollama-Jobs stoppen. |
| Upload schlägt fehl | Max. 20 MB; erlaubt: pdf/jpg/jpeg/png/webp. Genauer Grund steht als Fehlermeldung im UI und im Log. |

## KI-Assistent: Performance-Realität (Pi 500)

- phi4-mini (3.8B, Q4_K_M) generiert mit ~2–4 tok/s → eine Assistent-Antwort dauert **60–220 s**. Das UI zeigt den Ladezustand; das ist für das Café-Setting akzeptabel (Frage stellen → weiter reparieren → Antwort lesen).
- Antworten sind auf 400 Token begrenzt (`NUM_PREDICT` in `app/assistant.py`); der System-Prompt fordert kompakte Stichpunkte.
- Kontext ist auf 6000 Zeichen gecappt (`build_context`); bei Überschreitung werden Dokumente/älteste Einträge zuerst gekürzt.
- Modell kalt (nach ~10 Min. Idle): erste Antwort plus ~1–2 Min. Ladezeit. Falls das stört: `OLLAMA_KEEP_ALIVE` in der ollama-Service-Datei erhöhen.

## Wichtige Hinweise

1. **Haftungsausschluss-Text** (`app/waiver_text.py`, Version `2026-08-28`) ist eine gängige Standard-Vorlage — **vor dem ersten echten Café-Termin juristisch gegenprüfen** (Vereinsrecht/Versicherung). Version anpassen = eine Zeile; alte Waiver bleiben mit ihrer Version dokumentiert.
2. **DSGVO:** Namen + Unterschriften sind personenbezogene Daten; sie liegen ausschließlich lokal (DB + `data/signatures/`). Backups ebenfalls nur lokal (`~/repair-backups/`). Im UI nur Vornamen/Pseudonyme erfassen.
3. **Demo-Daten:** Bereinigt am 29.08.2026 — die Abnahme-Test-Daten (Föhn, Toaster, Smoke-Test-Bohrer) wurden gelöscht; verbleibend ist nur das echte Gerät **Hameg HM705** (Ticket 3, Tagebuch + Handbücher + Unterschrift). Soll die DB vor dem ersten Café-Termin komplett leer starten: `systemctl stop repair-cafe && rm data/repair.db* data/signatures/* && sudo systemctl start repair-cafe`.
4. **Server:** gunicorn (2 Worker × 4 Threads, Timeout 300 s) statt Flask-Devserver; Unit in `scripts/repair-cafe.service`. Lange Assistent-Antworten blockieren das UI nicht.
5. **Sicherheit (bewusste Design-Entscheidung für ein geschlossenes Café-LAN):** Es gibt **keine Authentifizierung** — jeder im WLAN kann Daten lesen, ändern und löschen. Betrieb nur im vertrauenswürdigen Vereins-WLAN, nicht in offenen Netzen. `/api/documents/<id>/fetch` lädt serverseitig beliebige http(s)-URLs (SSRF-Restrisiko) — bei Bedarf URL-Whitelist in `app/documents.py` ergänzen. Keine Cookie-Authentifizierung, daher kein klassisches CSRF-Risiko.