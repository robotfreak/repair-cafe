"""Tests für FTS5-Volltextsuche (Task 6)."""
import sqlite3

import pytest

from app.db import get_db
from app.search import search

WAIVER = {
    "signed_name": "Max Mustermann",
    "accepted": True,
    "signature_data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
}


def create_device(client, name):
    resp = client.post("/api/devices", json={"name": name})
    assert resp.status_code == 201
    return resp.get_json()["id"]


def create_ticket(client, device_id, fault):
    resp = client.post(
        "/api/tickets",
        json={"device_id": device_id, "fault_description": fault, "waiver": WAIVER},
    )
    assert resp.status_code == 201
    return resp.get_json()


def add_entry(client, ticket_id, content, entry_type="diagnose"):
    resp = client.post(
        f"/api/tickets/{ticket_id}/entries",
        json={"content": content, "entry_type": entry_type},
    )
    assert resp.status_code == 201


def seed_two_tickets(client):
    """Zwei Geräte + zwei Tickets mit klar unterscheidbaren Begriffen."""
    d1 = create_device(client, "Multimeter Fluke 87")
    d2 = create_device(client, "Labornetzteil Voltcraft")
    t1 = create_ticket(client, d1, "Anzeige bleibt dunkel")
    t2 = create_ticket(client, d2, "Keine Ausgangsspannung")
    add_entry(client, t1["id"], "Multimeter Spannung mit Zweitgerät verglichen")
    add_entry(client, t2["id"], "Kondensator Netzteil Elko aufgequollen")
    return t1, t2


# ---------- Reine Funktion search() ----------

def test_search_finds_right_journal_entry(app_client, tmp_path):
    t1, t2 = seed_two_tickets(app_client)
    conn = get_db(str(tmp_path / "repair.db"))
    try:
        result = search(conn, "multimeter")
    finally:
        conn.close()

    hits = result["journal"]
    assert len(hits) == 1
    hit = hits[0]
    assert hit["kind"] == "journal"
    assert hit["ticket_id"] == t1["id"]
    assert hit["device_name"] == "Multimeter Fluke 87"
    assert "Multimeter Spannung" in hit["snippet"]
    assert hit["entry_type"] == "diagnose"
    assert hit["fault_description"] == "Anzeige bleibt dunkel"
    assert result["documents"] == []


def test_search_finds_documents_by_text_content(app_client, tmp_path):
    seed_two_tickets(app_client)
    conn = get_db(str(tmp_path / "repair.db"))
    try:
        conn.execute(
            "INSERT INTO documents (title, doc_type, text_content)"
            " VALUES ('Datenblatt Elko', 'datasheet', 'Der Kondensator 470uF im Netzteil')"
        )
        conn.commit()
        result = search(conn, "kondensator")
    finally:
        conn.close()

    hits = result["documents"]
    assert len(hits) == 1
    hit = hits[0]
    assert hit["kind"] == "document"
    assert hit["snippet"] == "Datenblatt Elko"
    assert hit["url"] is None
    assert hit["file_path"] is None
    # Der Seed-Journal-Eintrag für Ticket 2 enthält 'Kondensator' ebenfalls
    # (legitimer Journal-Treffer) — wichtig ist: der Dokument-Treffer ist da.
    assert any(h["kind"] == "document" and h["snippet"] == "Datenblatt Elko" for h in hits)


def test_search_special_characters_no_crash(app_client, tmp_path):
    seed_two_tickets(app_client)
    conn = get_db(str(tmp_path / "repair.db"))
    try:
        result = search(conn, "Kondensator (470µF)")
        empty = search(conn, 'mult"imeter')
    finally:
        conn.close()

    assert set(result) == {"journal", "documents"}
    # Kein Crash, leere Treffer sind ok
    assert isinstance(result["journal"], list)
    assert isinstance(empty, dict)


def test_search_respects_limit(app_client, tmp_path):
    seed_two_tickets(app_client)
    conn = get_db(str(tmp_path / "repair.db"))
    try:
        result = search(conn, "kondensator OR multimeter", limit=1)
    finally:
        conn.close()
    # Limit gilt je Kategorie; hier genügt: keine Exception, Struktur stimmt
    assert len(result["journal"]) <= 1


def test_search_or_operator_semantics(app_client, tmp_path):
    """Regression: 'a OR b' muss als ODER-Verknüpfung wirken, nicht als Phrase."""
    t1, t2 = seed_two_tickets(app_client)
    conn = get_db(str(tmp_path / "repair.db"))
    try:
        result = search(conn, "kondensator OR multimeter")
    finally:
        conn.close()
    ticket_ids = {h["ticket_id"] for h in result["journal"]}
    assert ticket_ids == {t1["id"], t2["id"]}


# ---------- Route GET /api/search ----------

def test_route_search_returns_journal_hits(app_client):
    seed_two_tickets(app_client)
    resp = app_client.get("/api/search?q=multimeter")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["journal"]) == 1
    assert data["journal"][0]["device_name"] == "Multimeter Fluke 87"


def test_route_search_without_q_400(app_client):
    for url in ("/api/search", "/api/search?q=", "/api/search?q=%20%20"):
        resp = app_client.get(url)
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "Suchbegriff erforderlich"}


def test_route_search_fts_error_400(app_client, monkeypatch):
    import app.search as search_module

    def broken(conn, query, limit=20):
        raise sqlite3.OperationalError("fts5: syntax error")

    monkeypatch.setattr(search_module, "search", broken)
    resp = app_client.get("/api/search?q=test")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Ungültige Suchanfrage"}