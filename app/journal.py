import flask

from app.db import get_request_db

bp = flask.Blueprint("journal", __name__)

CONTENT_MAX = 5000
AUTHOR_MAX = 100

ENTRY_TYPES = ("notiz", "diagnose", "schritt", "ersatzteil", "ergebnis")

INVALID_TYPE_MSG = "Ungültiger Eintragstyp"


@bp.route("/api/tickets/<int:ticket_id>/entries", methods=["POST"])
def create_entry(ticket_id):
    payload = flask.request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}

    conn = get_request_db(flask.current_app)

    if conn.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
        return {"error": "Laufzettel nicht gefunden"}, 404

    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        return {"error": "Inhalt ist erforderlich"}, 400
    content = content.strip()
    if len(content) > CONTENT_MAX:
        return {"error": "Inhalt darf höchstens 5000 Zeichen lang sein"}, 400

    author = payload.get("author")
    if author is not None:
        if not isinstance(author, str):
            return {"error": "author muss ein Textfeld sein"}, 400
        author = author.strip()
        if len(author) > AUTHOR_MAX:
            return {"error": "author darf höchstens 100 Zeichen lang sein"}, 400
        author = author or None

    entry_type = payload.get("entry_type") or "notiz"
    if entry_type not in ENTRY_TYPES:
        return {"error": INVALID_TYPE_MSG}, 400

    cur = conn.execute(
        "INSERT INTO journal_entries (ticket_id, author, entry_type, content)"
        " VALUES (?, ?, ?, ?)",
        (ticket_id, author, entry_type, content),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM journal_entries WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return dict(row), 201


@bp.route("/api/tickets/<int:ticket_id>/entries/<int:entry_id>", methods=["PATCH"])
def update_entry(ticket_id, entry_id):
    """Nachträgliche Korrektur eines Tagebucheintrags (Trim + Pflicht-Prüfung)."""
    payload = flask.request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}

    conn = get_request_db(flask.current_app)
    row = conn.execute(
        "SELECT * FROM journal_entries WHERE id = ? AND ticket_id = ?",
        (entry_id, ticket_id),
    ).fetchone()
    if row is None:
        return {"error": "Eintrag nicht gefunden"}, 404

    fields, params = [], []
    if "content" in payload:
        content = payload.get("content")
        if not isinstance(content, str) or not content.strip():
            return {"error": "Inhalt ist erforderlich"}, 400
        content = content.strip()
        if len(content) > CONTENT_MAX:
            return {"error": "Inhalt darf höchstens 5000 Zeichen lang sein"}, 400
        fields.append("content = ?")
        params.append(content)
    if "entry_type" in payload:
        entry_type = payload.get("entry_type")
        if entry_type not in ENTRY_TYPES:
            return {"error": INVALID_TYPE_MSG}, 400
        fields.append("entry_type = ?")
        params.append(entry_type)
    if "author" in payload:
        who = payload.get("author")
        if who is not None and not isinstance(who, str):
            return {"error": "author muss ein Textfeld sein"}, 400
        who = (who or "").strip() or None
        if who and len(who) > AUTHOR_MAX:
            return {"error": "author darf höchstens 100 Zeichen lang sein"}, 400
        fields.append("edited_by = ?")
        params.append(who)
        # Nachtrag: Einträge ohne Autor („unbekannt") bekommen beim ersten
        # Bearbeiten den übermittelten Namen als Original-Autor gesetzt.
        if who and row["author"] is None:
            fields.append("author = ?")
            params.append(who)

    if not fields:
        return {"error": "Keine gültigen Felder zum Aktualisieren übergeben"}, 400

    fields.append("edited_at = datetime('now')")
    params.extend([entry_id, ticket_id])
    conn.execute(
        f"UPDATE journal_entries SET {', '.join(fields)}"
        " WHERE id = ? AND ticket_id = ?",
        params,
    )
    conn.commit()
    updated = conn.execute(
        "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
    ).fetchone()
    return dict(updated)


@bp.route("/api/tickets/<int:ticket_id>/entries/<int:entry_id>", methods=["DELETE"])
def delete_entry(ticket_id, entry_id):
    conn = get_request_db(flask.current_app)
    row = conn.execute(
        "SELECT id FROM journal_entries WHERE id = ? AND ticket_id = ?",
        (entry_id, ticket_id),
    ).fetchone()
    if row is None:
        return {"error": "Eintrag nicht gefunden"}, 404

    conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
    conn.commit()
    return {"ok": True}


@bp.route("/api/tickets/<int:ticket_id>/entries", methods=["GET"])
def list_entries(ticket_id):
    conn = get_request_db(flask.current_app)

    if conn.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
        return {"error": "Laufzettel nicht gefunden"}, 404

    rows = conn.execute(
        "SELECT * FROM journal_entries WHERE ticket_id = ?"
        " ORDER BY created_at ASC, id ASC",
        (ticket_id,),
    ).fetchall()
    return [dict(r) for r in rows]