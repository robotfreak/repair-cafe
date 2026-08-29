"""Tests für Journal-Blueprint (Tagebuch-Einträge, Task 5)."""
import pytest

from app.db import get_db


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


def entries_path(ticket_id):
    return f"/api/tickets/{ticket_id}/entries"


# ---------- POST ----------

def test_create_entry_201(app_client):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    resp = app_client.post(
        entries_path(ticket["id"]),
        json={"content": "Netzteil geprüft, keine Spannung", "author": "Anna"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["ticket_id"] == ticket["id"]
    assert data["content"] == "Netzteil geprüft, keine Spannung"
    assert data["author"] == "Anna"
    assert data["entry_type"] == "notiz"
    assert data["created_at"]


def test_create_entry_with_type(app_client):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    resp = app_client.post(
        entries_path(ticket["id"]),
        json={"content": "Kondensator C7 defekt", "entry_type": "diagnose"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["entry_type"] == "diagnose"


def test_create_entry_invalid_type_400(app_client):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    resp = app_client.post(
        entries_path(ticket["id"]),
        json={"content": "Test", "entry_type": "quatsch"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Ungültiger Eintragstyp"


def test_create_entry_empty_content_400(app_client):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    for content in (None, "", "   "):
        resp = app_client.post(entries_path(ticket["id"]), json={"content": content})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Inhalt ist erforderlich"


def test_create_entry_ticket_missing_404(app_client):
    resp = app_client.post("/api/tickets/9999/entries", json={"content": "Test"})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Laufzettel nicht gefunden"


# ---------- GET ----------

def test_list_entries_ascending(app_client):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    for text in ["Erster Eintrag", "Zweiter Eintrag", "Dritter Eintrag"]:
        resp = app_client.post(entries_path(ticket["id"]), json={"content": text})
        assert resp.status_code == 201

    resp = app_client.get(entries_path(ticket["id"]))
    assert resp.status_code == 200
    items = resp.get_json()
    assert [e["content"] for e in items] == [
        "Erster Eintrag",
        "Zweiter Eintrag",
        "Dritter Eintrag",
    ]
    assert items[0]["id"] < items[1]["id"] < items[2]["id"]


def test_list_entries_ticket_missing_404(app_client):
    resp = app_client.get("/api/tickets/9999/entries")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Laufzettel nicht gefunden"


# ---------- FTS-Trigger ----------

def test_journal_fts_populated_on_insert(app_client, tmp_path):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    resp = app_client.post(
        entries_path(ticket["id"]),
        json={"content": "Mit dem Multimeter Spannung gemessen", "entry_type": "schritt"},
    )
    assert resp.status_code == 201

    conn = get_db(str(tmp_path / "repair.db"))
    try:
        count = conn.execute(
            "SELECT count(*) AS n FROM journal_fts WHERE journal_fts MATCH 'multimeter'"
        ).fetchone()["n"]
    finally:
        conn.close()
    assert count > 0