# Repair-Café Laufzettel-System

Lokales Verwaltungssystem für Repair-Cafés auf dem Raspberry Pi 500: Laufzettel-Board,
Reparatur-Tagebuch mit Volltextsuche und Dokumenten-/Datenblatt-Verwaltung
(100% lokal — keine Cloud, DSGVO-freundlich).

**Alle Daten bleiben auf dem Pi.** Es gibt keine externe API, keinen API-Key, keine Cloud-Anbindung.
Für KI-Reparaturhilfe nutzt das Café einen externen Gemini-Gem (separates Tool, Bestandteil
dieses Systems nicht mehr — der frühere lokale ollama-Assistent wurde entfernt).

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
| **KI-Assistent** | Pro Ticket ein Chat mit Verlauf (Rückfragen möglich): sammelt automatisch Gerät, Fehler, Tagebuch, Treffer aus früheren Reparaturen und Manual-Ausschnitte als Kontext. Der System-Prompt folgt dem bewährten Gem-Profil: **Sicherheit vor allem** (Netzstecker, Akku, Kondensatoren entladen; bei Hochspannungs-Geräten wie Mikrowellen-Inverter oder Röhren-TV wird von Eigenreparatur abgeraten), dann phasenbasierte Hilfe (Diagnose → Öffnen → Reparatur → Zusammenbau & Test) mit jeweils nur einem nächsten Schritt und einer Rückfrage zum Zwischenstand. Läuft 100% lokal. |
| **VDE/DGUV-Prüfung (optional)** | Geräte tragen eine Schutzklasse (SK I/II/III, optional Heizleistung kW). Am Laufzettel erscheint je Schutzklasse eine Checkliste nach **DIN VDE 0701-0702** mit Grenzwerten; Messwerte werden serverseitig bewertet. **Prüfmittel-Verwaltung:** Messgeräte (Name, Seriennummer, „kalibriert bis") liegen in der DB und werden per Dropdown zugeordnet — jede Prüfung dokumentiert das verwendete Messgerät mit Snapshot (Name · SN · Kalibrierung) in beiden Drucken. **Die Prüfung ist freiwillig** — keine Pflicht für die Rückgabe; Messmittel sind derzeit nicht vorhanden. |
| **Druckansicht** | Ticket-Ansicht → **Laufzettel** (A5-hoch, 2 Seiten: Kopf + Haftungsausschluss-Referenz + Ankreuzfelder + Notizen · VDE-Prüfblock + Tagebuch + Dokumente), **separates VDE-Messprotokoll** (A4-hoch: Kopfdaten, Messgrößen-/Grenzwert-Tabelle, Gesamturteil, Unterschriftszeilen) und **A4-Haftungsausschluss** (Volltext der Reparatur- und Haftungsvereinbarung mit Version + Unterschrift im Kasten). Ohne gespeicherte Prüfung wird das Protokoll als **Blanko-Formular** zum handschriftlichen Ausfüllen gedruckt. |

## Architektur

```
Tablet (Browser, ein Gerät)
   │  http://pi:5002
   ▼
Flask (systemd: repair-cafe.service)  ──►  SQLite data/repair.db (WAL, FTS5)
   │                                        data/documents/  data/signatures/
```

- **Backend:** Python 3.11 (`.venv`), Flask-Blueprints pro Domain (`app/devices.py`, `app/tickets.py`, `app/journal.py`, `app/search.py`, `app/documents.py`, `app/waivers.py`, `app/equipment.py`).
- **Frontend:** Vanilla JS Einseiten-App (`static/app.js`, Hash-Routing), kein Framework, kein Build-Schritt.
- **Tests:** pytest-Suite (TDD-entwickelt).

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
| VDE-Prüfung fehlt am Laufzettel | Das Gerät hat keine Schutzklasse. Im Geräte-Tab aufklappen, Schutzklasse setzen (SK I/II/III) — danach erscheint die Prüfung (freiwillig) am Ticket. |
| Upload schlägt fehl | Max. 20 MB; erlaubt: pdf/jpg/jpeg/png/webp. Genauer Grund steht als Fehlermeldung im UI und im Log. |

## Wichtige Hinweise

1. **Haftungs­vereinbarung** (`app/waiver_text.py`, Version `2026-08-30`): überarbeitete „Reparatur- und Haftungsvereinbarung" (Internetvorlage, verschmolzen mit den bisherigen Punkten) — **vor dem ersten echten Café-Termin juristisch gegenprüfen** (Vereinsrecht/Versicherung). Version anpassen = eine Zeile; alte Waiver bleiben mit ihrer Version dokumentiert.
2. **DSGVO:** Namen + Unterschriften sind personenbezogene Daten; sie liegen ausschließlich lokal (DB + `data/signatures/`). Backups ebenfalls nur lokal (`~/repair-backups/`). Im UI nur Vornamen/Pseudonyme erfassen.
3. **Demo-Daten:** Bereinigt am 29.08.2026 — die Abnahme-Test-Daten (Föhn, Toaster, Smoke-Test-Bohrer) wurden gelöscht; verbleibend ist nur das echte Gerät **Hameg HM705** (Ticket 3, Tagebuch + Handbücher + Unterschrift). Soll die DB vor dem ersten Café-Termin komplett leer starten: `systemctl stop repair-cafe && rm data/repair.db* data/signatures/* && sudo systemctl start repair-cafe`.
4. **Server:** gunicorn (2 Worker × 4 Threads, Timeout 300 s) statt Flask-Devserver; Unit in `scripts/repair-cafe.service`.
5. **Sicherheit (bewusste Design-Entscheidung für ein geschlossenes Café-LAN):** Es gibt **keine Authentifizierung** — jeder im WLAN kann Daten lesen, ändern und löschen. Betrieb nur im vertrauenswürdigen Vereins-WLAN, nicht in offenen Netzen. `/api/documents/<id>/fetch` lädt serverseitig beliebige http(s)-URLs (SSRF-Restrisiko) — bei Bedarf URL-Whitelist in `app/documents.py` ergänzen. Keine Cookie-Authentifizierung, daher kein klassisches CSRF-Risiko.