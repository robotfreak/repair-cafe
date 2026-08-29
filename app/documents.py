"""Dokumente: Upload mit PDF-Textextraktion, URL-Fetch, Datei-Ausgabe (Task 7)."""
import io
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

import flask
import pypdf

from app.db import get_request_db

bp = flask.Blueprint("documents", __name__)

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
DOC_TYPES = ("datasheet", "manual", "schema", "foto", "sonstiges")

TITLE_MAX = 300
DOWNLOAD_TIMEOUT = 30
DOWNLOAD_MAX_BYTES = MAX_UPLOAD_BYTES

TYPE_MSG = "Ungültiger Dokumenttyp"
EXT_MSG = "Dateityp nicht erlaubt. Erlaubt: pdf, jpg, jpeg, png, webp"
DOWNLOAD_FAILED_MSG = "Download fehlgeschlagen"
SIZE_MSG = "Datei zu groß (max. 20 MB)"
MISSING_MSG = "Dokument nicht gefunden"
NOT_FOUND = ({"error": MISSING_MSG}, 404)

MIMETYPES = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


class ResponseTooLarge(Exception):
    """Download überschreitet DOWNLOAD_MAX_BYTES."""


def extract_pdf_text(file_storage_or_bytes) -> str | None:
    """Extrahiert den Text aller Seiten eines PDFs.

    Akzeptiert bytes oder ein File-like-Objekt (z.B. Flask FileStorage).
    Gibt None zurück bei leerem/Whitespace-Ergebnis, verschlüsseltem PDF
    oder pypdf-Fehlern (z.B. gescannte PDFs ohne Textlayer) — wirft niemals.
    """
    try:
        if isinstance(file_storage_or_bytes, (bytes, bytearray)):
            data = bytes(file_storage_or_bytes)
        else:
            data = file_storage_or_bytes.read()
        if not data:
            return None
        reader = pypdf.PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            return None
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
        return text if text else None
    except Exception:
        return None


def extension_from_filename(filename):
    """Letzte Extension aus einem Dateinamen (ohne Punkt, lowercase)."""
    return os.path.splitext(filename)[1].lstrip(".").lower()


def extension_from_url(url):
    """Extension aus dem URL-Pfad (ohne Query-String); default 'pdf'."""
    path = urllib.parse.urlparse(url).path
    return extension_from_filename(path) or "pdf"


def download_url(url, timeout=DOWNLOAD_TIMEOUT):
    """Lädt eine URL und liest maximal DOWNLOAD_MAX_BYTES Bytes.

    Rückgabe: (content_type, data). Wirft urllib.error.URLError/HTTPError,
    TimeoutError und ResponseTooLarge.
    """
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        content_type = resp.headers.get_content_type()
        data = resp.read(DOWNLOAD_MAX_BYTES + 1)
    if len(data) > DOWNLOAD_MAX_BYTES:
        raise ResponseTooLarge()
    return content_type, data


def _save_document_file(data_dir, data, ext):
    """Speichert Bytes unter DATA_DIR/documents/<uuid4hex>.<ext>.

    Gibt (relativer_pfad, text_content) zurück; text_content nur bei PDFs.
    """
    doc_dir = os.path.join(data_dir, "documents")
    os.makedirs(doc_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(doc_dir, filename), "wb") as fh:
        fh.write(data)

    text_content = None
    if ext == "pdf":
        text_content = extract_pdf_text(data)
    return f"documents/{filename}", text_content


def _validate_reference_ids(conn, device_id, ticket_id):
    """Prüft device_id/ticket_id (None = nicht gesetzt).

    Rückgabe: None bei Erfolg, sonst (status, fehlermeldung).
    """
    if device_id is not None:
        if conn.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone() is None:
            return 404, "Gerät nicht gefunden"
    if ticket_id is not None:
        if conn.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return 404, "Laufzettel nicht gefunden"
    return None


def _parse_int(value):
    """Konvertiert zu int; None bleibt None; ungültige Werte → None."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _doc_dict(row):
    return dict(row)


@bp.route("/api/documents", methods=["POST"])
def create_document():
    conn = get_request_db(flask.current_app)

    if flask.request.is_json:
        payload = flask.request.get_json(silent=True) or {}
        title = payload.get("title")
        doc_type = payload.get("doc_type")
        device_id = _parse_int(payload.get("device_id"))
        ticket_id = _parse_int(payload.get("ticket_id"))
        file_storage = None
        url = payload.get("url")
    else:
        title = flask.request.form.get("title")
        doc_type = flask.request.form.get("doc_type")
        device_id = _parse_int(flask.request.form.get("device_id"))
        ticket_id = _parse_int(flask.request.form.get("ticket_id"))
        file_storage = flask.request.files.get("file")
        url = flask.request.form.get("url") or None

    # --- Validierung ---
    if not isinstance(title, str) or not title.strip():
        return {"error": "Titel ist erforderlich"}, 400
    title = title.strip()
    if len(title) > TITLE_MAX:
        return {"error": f"Titel darf höchstens {TITLE_MAX} Zeichen lang sein"}, 400

    if doc_type is None or (isinstance(doc_type, str) and not doc_type.strip()):
        doc_type = "datasheet"
    if doc_type not in DOC_TYPES:
        return {"error": TYPE_MSG}, 400

    ref_error = _validate_reference_ids(conn, device_id, ticket_id)
    if ref_error is not None:
        status, message = ref_error
        return {"error": message}, status

    has_file = file_storage is not None and getattr(file_storage, "filename", "") != ""
    if not has_file and not url:
        return {"error": "Datei oder URL erforderlich"}, 400

    # --- Datei-Upload ---
    if has_file:
        ext = extension_from_filename(file_storage.filename)
        if ext not in ALLOWED_EXTENSIONS:
            return {"error": EXT_MSG}, 400

        # Größe prüfen: content_length (falls geliefert) als Vorfilter,
        # definitive Prüfung nach dem Speichern via os.path.getsize.
        if (file_storage.content_length or 0) > MAX_UPLOAD_BYTES:
            return {"error": SIZE_MSG}, 400

        data = file_storage.read()
        if len(data) > MAX_UPLOAD_BYTES:
            return {"error": SIZE_MSG}, 400

        data_dir = flask.current_app.config["DATA_DIR"]
        rel_path, text_content = _save_document_file(data_dir, data, ext)

        # Nach dem Speichern nochmal auf der Platte prüfen (multipart kann
        # abweichen); im Fehlerfall Datei wieder löschen.
        full = os.path.join(data_dir, rel_path)
        if os.path.getsize(full) > MAX_UPLOAD_BYTES:
            os.remove(full)
            return {"error": SIZE_MSG}, 400

        url_value = None
    else:
        # --- Nur-URL-Eintrag (KEIN Download hier — das macht /fetch) ---
        if not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
            return {"error": "URL muss mit http:// oder https:// beginnen"}, 400
        rel_path = None
        text_content = None
        url_value = url.strip()

    # --- Duplikatschutz: identische Datei am selben Ticket/Gerät ablehnen ---
    digest = None
    if has_file:
        import hashlib
        digest = hashlib.sha256(data).hexdigest()
        dup = conn.execute(
            "SELECT id FROM documents WHERE content_hash = ?"
            " AND COALESCE(ticket_id, -1) = COALESCE(?, -1)"
            " AND COALESCE(device_id, -1) = COALESCE(?, -1)",
            (digest, ticket_id, device_id),
        ).fetchone()
        if dup:
            return {"error": "Dieses Dokument existiert an dieser Stelle bereits (identische Datei)"}, 409

    cur = conn.execute(
        "INSERT INTO documents (device_id, ticket_id, title, doc_type, url, file_path,"
        " text_content, content_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (device_id, ticket_id, title, doc_type, url_value, rel_path, text_content, digest),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM documents WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _doc_dict(row), 201


@bp.route("/api/documents/<int:doc_id>/fetch", methods=["POST"])
def fetch_document(doc_id):
    conn = get_request_db(flask.current_app)
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row is None:
        return NOT_FOUND

    url = row["url"]
    if not url:
        return {"error": "Kein URL hinterlegt"}, 400

    try:
        _content_type, data = download_url(url, timeout=DOWNLOAD_TIMEOUT)
    except ResponseTooLarge:
        return {"error": "Zieldatei zu groß"}, 400
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None) or exc
        return {"error": f"{DOWNLOAD_FAILED_MSG}: {reason}"}, 502

    ext = extension_from_url(url)
    if ext not in ALLOWED_EXTENSIONS:
        ext = "pdf"

    data_dir = flask.current_app.config["DATA_DIR"]
    rel_path, text_content = _save_document_file(data_dir, data, ext)

    conn.execute(
        "UPDATE documents SET file_path = ?, text_content = ? WHERE id = ?",
        (rel_path, text_content, doc_id),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return _doc_dict(row), 200


@bp.route("/api/documents", methods=["GET"])
def list_documents():
    conn = get_request_db(flask.current_app)

    clauses = []
    params = []
    for param, column in (("device_id", "device_id"), ("ticket_id", "ticket_id")):
        raw = flask.request.args.get(param)
        if raw is None or raw == "":
            continue
        value = _parse_int(raw)
        if value is None:
            return {"error": "Ungültiger Filterwert"}, 400
        clauses.append(f"{column} = ?")
        params.append(value)

    sql = "SELECT * FROM documents"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC, id DESC"

    rows = conn.execute(sql, params).fetchall()
    return [_doc_dict(r) for r in rows]


@bp.route("/api/documents/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    conn = get_request_db(flask.current_app)
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row is None:
        return NOT_FOUND
    return _doc_dict(row)


@bp.route("/api/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    """Dokument löschen (DB-Zeile + physische Datei, falls vorhanden)."""
    conn = get_request_db(flask.current_app)
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row is None:
        return NOT_FOUND

    file_path = row["file_path"]
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()

    if file_path:
        data_dir = os.path.abspath(flask.current_app.config["DATA_DIR"])
        full_path = os.path.abspath(
            os.path.normpath(os.path.join(data_dir, file_path))
        )
        if (os.path.commonpath([data_dir, full_path]) == data_dir
                and os.path.isfile(full_path)):
            try:
                os.remove(full_path)
            except OSError:
                pass  # DB gelöscht; Restdatei ist unkritisch
    return {"ok": True}


@bp.route("/api/documents/<int:doc_id>/file", methods=["GET"])
def get_document_file(doc_id):
    conn = get_request_db(flask.current_app)
    row = conn.execute("SELECT file_path FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row is None or not row["file_path"]:
        return NOT_FOUND

    # Pfad-Schutz-Muster aus waivers.py: commonpath-Vergleich gegen DATA_DIR.
    data_dir = os.path.abspath(flask.current_app.config["DATA_DIR"])
    full_path = os.path.abspath(
        os.path.normpath(os.path.join(data_dir, row["file_path"]))
    )
    if os.path.commonpath([data_dir, full_path]) != data_dir:
        return NOT_FOUND
    if not os.path.isfile(full_path):
        return NOT_FOUND

    ext = extension_from_filename(full_path)
    mimetype = MIMETYPES.get(ext, "application/octet-stream")
    return flask.send_file(full_path, mimetype=mimetype)