"""FTS5-Volltextsuche über Laufzettel-Journal und Dokumente (Task 6)."""
import sqlite3

import flask

from app.db import get_request_db

bp = flask.Blueprint("search", __name__)

DEFAULT_LIMIT = 20


def search(conn, query, limit=DEFAULT_LIMIT):
    """Durchsucht journal_fts und doc_fts nach query.

    Reine Funktion (conn wird injiziert, kein Flask nötig).
    Die Query wird tokenisiert: jeder Begriff wird als double-quoted
    FTS5-String entschärft und die Begriffe werden mit OR verknüpft,
    so dass Sonderzeichen und FTS5-Syntax nicht crashen und mehrere
    Begriffe als ODER-Verknüpfung wirken (nicht als eine Phrase).
    Rückgabe: {'journal': [dicts], 'documents': [dicts]}
    """
    terms = [t for t in query.replace('"', " ").split() if t]
    if not terms:
        terms = [""]
    safe = " OR ".join(f'"{t}"' for t in terms)

    journal_rows = conn.execute(
        "SELECT j.id, 'journal' AS kind, j.content AS snippet, j.entry_type,"
        " t.id AS ticket_id, t.fault_description, d.name AS device_name,"
        " bm25(journal_fts) AS rank"
        " FROM journal_fts f"
        " JOIN journal_entries j ON j.id = f.rowid"
        " JOIN tickets t ON t.id = j.ticket_id"
        " JOIN devices d ON d.id = t.device_id"
        " WHERE journal_fts MATCH ?"
        " ORDER BY rank"
        " LIMIT ?",
        (safe, limit),
    ).fetchall()

    document_rows = conn.execute(
        "SELECT doc.id, 'document' AS kind, doc.title AS snippet, doc.url,"
        " doc.file_path, doc.device_id, doc.ticket_id, bm25(doc_fts) AS rank"
        " FROM doc_fts f"
        " JOIN documents doc ON doc.id = f.rowid"
        " WHERE doc_fts MATCH ?"
        " ORDER BY rank"
        " LIMIT ?",
        (safe, limit),
    ).fetchall()

    return {
        "journal": [dict(r) for r in journal_rows],
        "documents": [dict(r) for r in document_rows],
    }


@bp.route("/api/search", methods=["GET"])
def search_route():
    query = flask.request.args.get("q", "")
    if not query.strip():
        return {"error": "Suchbegriff erforderlich"}, 400

    conn = get_request_db(flask.current_app)
    try:
        result = search(conn, query)
    except sqlite3.OperationalError:
        return {"error": "Ungültige Suchanfrage"}, 400
    return result