#!/usr/bin/env python3
"""Backup der Repair-Café-Datenbank UND aller Datei-Anhänge.

- DB via Pythons sqlite3-Online-Backup-API (sicher bei laufendem Server, WAL-freundlich)
- signatures/ und documents/ werden als Zip mit gesichert (Unterschriften sind
  rechtlich relevante Anlagen — ohne sie wäre ein DB-Backup wertlos)
- Behält die letzten 30 Tagesbackups

Cron-Eintrag (bereits installiert):
  0 20 * * * /home/pi/repair-cafe/.venv/bin/python /home/pi/repair-cafe/scripts/backup.py >> /tmp/repair_backup.log 2>&1
"""
import os
import sqlite3
import sys
import time
import zipfile

DB_PATH = "/home/pi/repair-cafe/data/repair.db"
DATA_DIR = "/home/pi/repair-cafe/data"
DEST_DIR = os.environ.get("REPAIR_BACKUP_DIR", "/home/pi/repair-backups")
KEEP_DAYS = 30


def backup_files(zip_path):
    """Packt signatures/ + documents/ in ein Zip. False, wenn nichts da ist."""
    entries = []
    for sub in ("signatures", "documents"):
        d = os.path.join(DATA_DIR, sub)
        if os.path.isdir(d):
            for name in os.listdir(d):
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    entries.append((p, sub + "/" + name))
    if not entries:
        return False
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, arcname in entries:
            zf.write(full, arcname=arcname)
    return True


def main():
    os.makedirs(DEST_DIR, exist_ok=True)
    stamp = time.strftime("%F")
    dest = os.path.join(DEST_DIR, f"repair-{stamp}.db")

    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()

    files_zip = os.path.join(DEST_DIR, f"repair-files-{stamp}.zip")
    has_files = backup_files(files_zip)

    cutoff = time.time() - KEEP_DAYS * 86400
    removed = 0
    for name in os.listdir(DEST_DIR):
        p = os.path.join(DEST_DIR, name)
        if not os.path.isfile(p):
            continue
        is_db = name.startswith("repair-") and name.endswith(".db")
        is_zip = name.startswith("repair-files-") and name.endswith(".zip")
        if (is_db or is_zip) and os.path.getmtime(p) < cutoff:
            os.remove(p)
            removed += 1

    files_note = f" + {files_zip}" if has_files else ""
    print(f"{time.strftime('%F %T')} Backup ok: {dest} ({os.path.getsize(dest)} Bytes){files_note}, {removed} alte gelöscht")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"{time.strftime('%F %T')} BACKUP FEHLGESCHLAGEN: {exc}", file=sys.stderr)
        sys.exit(1)