import hashlib
import os
import pathlib
import sqlite3

import flask

SCHEMA = pathlib.Path(__file__).parent / "schema.sql"


def get_db(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    return db


def _migrate(db, path):
    """Migration für bestehende DBs (CREATE TABLE IF NOT EXISTS ergänzt keine Spalten)."""
    existing = {r[1] for r in db.execute("PRAGMA table_info(devices)")}
    if "schutzklasse" not in existing:
        db.execute("ALTER TABLE devices ADD COLUMN schutzklasse TEXT"
                   " CHECK(schutzklasse IS NULL OR schutzklasse IN ('I','II','III'))")
    if "heating_kw" not in existing:
        db.execute("ALTER TABLE devices ADD COLUMN heating_kw REAL"
                   " CHECK(heating_kw IS NULL OR heating_kw > 0)")

    journal_cols = {r[1] for r in db.execute("PRAGMA table_info(journal_entries)")}
    if "edited_at" not in journal_cols:
        db.execute("ALTER TABLE journal_entries ADD COLUMN edited_at TEXT")
    if "edited_by" not in journal_cols:
        db.execute("ALTER TABLE journal_entries ADD COLUMN edited_by TEXT")

    doc_cols = {r[1] for r in db.execute("PRAGMA table_info(documents)")}
    if "content_hash" not in doc_cols:
        db.execute("ALTER TABLE documents ADD COLUMN content_hash TEXT")

    # Einmaliger Backfill: SHA-256 für bereits gespeicherte Dateien nachtragen
    data_dir = os.path.dirname(os.path.abspath(path))
    stale = db.execute(
        "SELECT id, file_path FROM documents"
        " WHERE file_path IS NOT NULL AND (content_hash IS NULL OR content_hash = '')"
    ).fetchall()
    for row in stale:
        full = os.path.join(data_dir, row["file_path"])
        if os.path.exists(full):
            with open(full, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            db.execute("UPDATE documents SET content_hash = ? WHERE id = ?",
                       (digest, row["id"]))


def init_db(path):
    db = get_db(path)
    db.executescript(SCHEMA.read_text())
    _migrate(db, path)
    db.commit()
    return db


def get_request_db(app):
    """Eine Connection pro Request, via flask.g gecacht."""
    if not hasattr(flask.g, "_db"):
        flask.g._db = get_db(app.config["DB_PATH"])
    return flask.g._db