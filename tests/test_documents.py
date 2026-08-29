"""Tests für Dokumente-Blueprint: Upload, PDF-Extraktion, Fetch, Datei-Ausgabe (Task 7)."""
import io

import app.documents as documents_module

# Funktionierendes Minimal-PDF: gleiche Objektstruktur wie das Task-Template,
# aber mit korrekter xref-Tabelle und exakter /Length — pypdf verweigert
# sonst das Parsing ("startxref not found") und liefert keinen Text.
_MINIMAL_STREAM = b"BT /F1 12 Tf 72 720 Td (Kondensator 470uF geplatzt) Tj ET\n"


def _build_minimal_pdf():
    objs = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(_MINIMAL_STREAM)).encode() + b">>stream\n"
        + _MINIMAL_STREAM + b"endstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj".encode() + body + b"endobj\n"
    xref_pos = len(out)
    count = len(objs) + 1
    out += f"xref\n0 {count}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer<</Root 1 0 R/Size {count}>>\nstartxref\n{xref_pos}\n%%EOF".encode()
    return bytes(out)


MINIMAL_PDF = _build_minimal_pdf()

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f030005fe02fea72d1e48"
    "0000000049454e44ae426082"
)


def create_device(client, name="Testgerät"):
    resp = client.post("/api/devices", json={"name": name})
    assert resp.status_code == 201
    return resp.get_json()["id"]


def create_ticket(client, device_id):
    resp = client.post(
        "/api/tickets",
        json={
            "device_id": device_id,
            "fault_description": "Kaputt",
            "waiver": {
                "signed_name": "Max Mustermann",
                "accepted": True,
                "signature_data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            },
        },
    )
    assert resp.status_code == 201
    return resp.get_json()


# ---------- extract_pdf_text ----------

def test_extract_pdf_text_reads_minimal_pdf():
    from app.documents import extract_pdf_text

    text = extract_pdf_text(MINIMAL_PDF)
    assert text is not None
    assert "Kondensator" in text


def test_extract_pdf_text_garbage_returns_none():
    from app.documents import extract_pdf_text

    assert extract_pdf_text(b"kein pdf") is None
    assert extract_pdf_text(b"") is None


def test_extract_pdf_text_accepts_file_storage():
    """Auch ein Flask FileStorage (File-like) wird akzeptiert."""
    from app.documents import extract_pdf_text

    storage = type("FakeStorage", (), {"read": lambda self: MINIMAL_PDF})()
    assert extract_pdf_text(storage) is not None


# ---------- POST /api/documents (Upload) ----------

def test_upload_pdf_201_and_extraction(app_client, tmp_path):
    device_id = create_device(app_client)
    resp = app_client.post(
        "/api/documents",
        data={
            "title": "Datenblatt Elko",
            "doc_type": "datasheet",
            "device_id": str(device_id),
            "file": (io.BytesIO(MINIMAL_PDF), "datasheet.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    doc = resp.get_json()
    assert doc["title"] == "Datenblatt Elko"
    assert doc["text_content"] is not None
    assert "Kondensator" in doc["text_content"]
    assert doc["file_path"].startswith("documents/")
    assert doc["url"] is None

    # Datei liegt physisch unter DATA_DIR/documents/
    saved = tmp_path / doc["file_path"]
    assert saved.is_file()
    assert saved.read_bytes() == MINIMAL_PDF


def test_upload_png_201_text_none(app_client):
    resp = app_client.post(
        "/api/documents",
        data={"title": "Foto Platine", "file": (io.BytesIO(PNG_1X1), "platine.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    doc = resp.get_json()
    assert doc["doc_type"] == "datasheet"  # Default
    assert doc["text_content"] is None
    assert doc["file_path"].endswith(".png")


def test_upload_txt_400(app_client):
    resp = app_client.post(
        "/api/documents",
        data={"title": "Notizen", "file": (io.BytesIO(b"hallo"), "notizen.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == (
        "Dateityp nicht erlaubt. Erlaubt: pdf, jpg, jpeg, png, webp"
    )


def test_upload_without_title_400(app_client):
    for title in (None, "", "   "):
        data = {"file": (io.BytesIO(PNG_1X1), "x.png")}
        if title is not None:
            data["title"] = title
        resp = app_client.post("/api/documents", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Titel ist erforderlich"


def test_upload_title_too_long_400(app_client):
    resp = app_client.post(
        "/api/documents",
        data={"title": "x" * 301, "file": (io.BytesIO(PNG_1X1), "x.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Titel darf höchstens 300 Zeichen lang sein"


def test_upload_wrong_doc_type_400(app_client):
    resp = app_client.post(
        "/api/documents",
        data={"title": "X", "doc_type": "quatsch", "file": (io.BytesIO(PNG_1X1), "x.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Ungültiger Dokumenttyp"


def test_upload_device_missing_404(app_client):
    resp = app_client.post(
        "/api/documents",
        data={"title": "X", "device_id": "9999", "file": (io.BytesIO(PNG_1X1), "x.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Gerät nicht gefunden"


def test_upload_ticket_missing_404(app_client):
    resp = app_client.post(
        "/api/documents",
        data={"title": "X", "ticket_id": "9999", "file": (io.BytesIO(PNG_1X1), "x.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Laufzettel nicht gefunden"


def test_upload_without_file_and_url_400(app_client):
    resp = app_client.post("/api/documents", data={"title": "Nur Titel"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Datei oder URL erforderlich"


def test_upload_url_only_201_no_download(app_client):
    resp = app_client.post(
        "/api/documents",
        json={"title": "Anleitung online", "url": "https://example.com/manual.pdf"},
    )
    assert resp.status_code == 201
    doc = resp.get_json()
    assert doc["url"] == "https://example.com/manual.pdf"
    assert doc["file_path"] is None
    assert doc["text_content"] is None


def test_upload_url_invalid_scheme_400(app_client):
    resp = app_client.post(
        "/api/documents",
        json={"title": "Ftp", "url": "ftp://example.com/manual.pdf"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "URL muss mit http:// oder https:// beginnen"


def test_upload_file_too_large_400(app_client, monkeypatch):
    monkeypatch.setattr(documents_module, "MAX_UPLOAD_BYTES", 10)
    resp = app_client.post(
        "/api/documents",
        data={"title": "Riesig", "file": (io.BytesIO(PNG_1X1), "gross.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Datei zu groß (max. 20 MB)"


def test_upload_scanned_pdf_no_textlayer_201(app_client):
    """Kein Crash, wenn pypdf keinen Text findet (gescanntes PDF)."""
    resp = app_client.post(
        "/api/documents",
        data={
            "title": "Gescannt",
            "file": (io.BytesIO(b"kaputte pdf daten mit .pdf endung"), "scan.pdf"),
        },
        content_type="multipart/form-data",
    )
    # extract_pdf_text liefert None, Upload selbst läuft durch:
    assert resp.status_code == 201
    assert resp.get_json()["text_content"] is None


# ---------- GET: Liste, Filter, Detail ----------

def test_list_documents_and_filters(app_client, tmp_path):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    conn_str = str(tmp_path / "repair.db")

    from app.db import get_db

    conn = get_db(conn_str)
    try:
        conn.execute(
            "INSERT INTO documents (device_id, ticket_id, title, doc_type, url)"
            " VALUES (?, ?, 'Doc A', 'manual', 'https://a.example/x.pdf')",
            (device_id, ticket["id"]),
        )
        conn.execute(
            "INSERT INTO documents (device_id, title, doc_type, url)"
            " VALUES (?, 'Doc B', 'schema', 'https://b.example/y.pdf')",
            (device_id,),
        )
        conn.commit()
    finally:
        conn.close()

    resp = app_client.get("/api/documents")
    assert resp.status_code == 200
    items = resp.get_json()
    assert [d["title"] for d in items] == ["Doc B", "Doc A"]  # created_at DESC

    resp = app_client.get(f"/api/documents?device_id={device_id}")
    assert resp.status_code == 200
    assert [d["title"] for d in resp.get_json()] == ["Doc B", "Doc A"]

    resp = app_client.get(f"/api/documents?ticket_id={ticket['id']}")
    assert resp.status_code == 200
    assert [d["title"] for d in resp.get_json()] == ["Doc A"]

    resp = app_client.get("/api/documents?device_id=abc")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Ungültiger Filterwert"


def test_get_document_detail(app_client, tmp_path):
    from app.db import get_db

    conn = get_db(str(tmp_path / "repair.db"))
    try:
        conn.execute("INSERT INTO documents (title) VALUES ('Nur Titel')")
        conn.commit()
    finally:
        conn.close()

    resp = app_client.get("/api/documents/1")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Nur Titel"

    resp = app_client.get("/api/documents/9999")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Dokument nicht gefunden"}


# ---------- GET /<id>/file ----------

def test_get_file_serves_pdf_bytes(app_client, tmp_path):
    device_id = create_device(app_client)
    resp = app_client.post(
        "/api/documents",
        data={"title": "Doku", "device_id": str(device_id), "file": (io.BytesIO(MINIMAL_PDF), "doku.pdf")},
        content_type="multipart/form-data",
    )
    doc_id = resp.get_json()["id"]

    resp = app_client.get(f"/api/documents/{doc_id}/file")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data.startswith(b"%PDF")


def test_get_file_png_mimetype(app_client):
    resp = app_client.post(
        "/api/documents",
        data={"title": "Foto", "file": (io.BytesIO(PNG_1X1), "foto.png")},
        content_type="multipart/form-data",
    )
    doc_id = resp.get_json()["id"]
    resp = app_client.get(f"/api/documents/{doc_id}/file")
    assert resp.status_code == 200
    assert resp.mimetype == "image/png"


def test_get_file_without_file_path_404(app_client, tmp_path):
    from app.db import get_db

    conn = get_db(str(tmp_path / "repair.db"))
    try:
        conn.execute(
            "INSERT INTO documents (title, url) VALUES ('Nur URL', 'https://x.example/a.pdf')"
        )
        conn.commit()
    finally:
        conn.close()
    resp = app_client.get("/api/documents/1/file")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Dokument nicht gefunden"}


def test_get_file_path_traversal_404(app_client, tmp_path):
    from app.db import get_db

    conn = get_db(str(tmp_path / "repair.db"))
    try:
        conn.execute(
            "INSERT INTO documents (title, file_path) VALUES ('Bösartig', '../../etc/passwd')"
        )
        conn.commit()
    finally:
        conn.close()
    resp = app_client.get("/api/documents/1/file")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Dokument nicht gefunden"}


def test_get_file_missing_on_disk_404(app_client, tmp_path):
    from app.db import get_db

    conn = get_db(str(tmp_path / "repair.db"))
    try:
        conn.execute(
            "INSERT INTO documents (title, file_path) VALUES ('Verschwunden', 'documents/gone.pdf')"
        )
        conn.commit()
    finally:
        conn.close()
    resp = app_client.get("/api/documents/1/file")
    assert resp.status_code == 404


def test_get_file_document_missing_404(app_client):
    resp = app_client.get("/api/documents/9999/file")
    assert resp.status_code == 404


# ---------- POST /<id>/fetch ----------

def test_fetch_downloads_and_extracts(app_client, tmp_path, monkeypatch):
    from app.db import get_db

    resp = app_client.post(
        "/api/documents",
        json={"title": "Manual", "url": "https://example.com/elko-470uf.pdf"},
    )
    doc_id = resp.get_json()["id"]

    def fake_download(url, timeout=30):
        return "pdf", MINIMAL_PDF

    monkeypatch.setattr(documents_module, "download_url", fake_download)

    resp = app_client.post(f"/api/documents/{doc_id}/fetch")
    assert resp.status_code == 200
    doc = resp.get_json()
    assert doc["file_path"] == "documents/" + doc["file_path"].split("/")[-1]
    assert doc["file_path"].endswith(".pdf")
    assert doc["text_content"] is not None
    assert "Kondensator" in doc["text_content"]

    # Datei liegt unter DATA_DIR/documents/
    saved = tmp_path / doc["file_path"]
    assert saved.is_file()
    assert saved.read_bytes() == MINIMAL_PDF


def test_fetch_url_too_large_400(app_client, tmp_path, monkeypatch):
    from app.db import get_db

    resp = app_client.post(
        "/api/documents",
        json={"title": "Riesig", "url": "https://example.com/big.pdf"},
    )
    doc_id = resp.get_json()["id"]

    class FakeResp:
        def read(self, n):
            return b"x" * 100

    monkeypatch.setattr(
        documents_module,
        "download_url",
        lambda url, timeout=30: (_ for _ in ()).throw(documents_module.ResponseTooLarge()),
    )
    resp = app_client.post(f"/api/documents/{doc_id}/fetch")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Zieldatei zu groß"


def test_fetch_network_error_502(app_client, tmp_path):
    """Echter Netzwerkfehler: localhost Port 1 (zu) → URLError → 502."""
    from app.db import get_db

    resp = app_client.post(
        "/api/documents",
        json={"title": "Lokal", "url": "http://127.0.0.1:1/x.pdf"},
    )
    doc_id = resp.get_json()["id"]
    resp = app_client.post(f"/api/documents/{doc_id}/fetch")
    assert resp.status_code == 502
    error = resp.get_json()["error"]
    assert error.startswith("Download fehlgeschlagen:")
    assert len(error) > len("Download fehlgeschlagen: ")  # Ursache vorhanden


def test_fetch_document_or_url_missing(app_client, tmp_path):
    from app.db import get_db

    conn = get_db(str(tmp_path / "repair.db"))
    try:
        conn.execute("INSERT INTO documents (title, file_path) VALUES ('X', 'documents/a.pdf')")
        conn.commit()
    finally:
        conn.close()

    resp = app_client.post("/api/documents/9999/fetch")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Dokument nicht gefunden"}

    # Dokument ohne URL:
    resp = app_client.post("/api/documents/1/fetch")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Kein URL hinterlegt"