"""Tests für Laufzettel/Tickets mit Statusmaschine und Pflicht-Waiver (Task 4)."""
import os
import sqlite3

import pytest  # noqa: F401

from app.tickets import TIMESTAMP_FIELD, TRANSITIONS, can_transition

PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
PNG_DATA_URL = "data:image/png;base64," + PNG_B64


def make_waiver(**overrides):
    w = {"signed_name": "Max Mustermann", "accepted": True, "signature_data_url": PNG_DATA_URL}
    w.update(overrides)
    return w


def create_device(client, name="Testgerät"):
    resp = client.post("/api/devices", json={"name": name})
    assert resp.status_code == 201
    return resp.get_json()["id"]


def create_ticket(client, device_id, **overrides):
    payload = {"device_id": device_id, "fault_description": "Läuft nicht", "waiver": make_waiver()}
    payload.update(overrides)
    resp = client.post("/api/tickets", json=payload)
    assert resp.status_code == 201
    return resp.get_json()


# ---------- Statusmaschine (reine Funktionen, ohne Flask) ----------

def test_transitions_constant():
    assert TRANSITIONS == {
        "offen": {"in_arbeit"},
        "in_arbeit": {"erfolgreich", "nicht_reparierbar", "offen"},
        "erfolgreich": {"abgeholt"},
        "nicht_reparierbar": {"abgeholt"},
        "abgeholt": set(),
    }


def test_timestamp_field_constant():
    assert TIMESTAMP_FIELD["in_arbeit"] == "started_at"
    assert TIMESTAMP_FIELD["erfolgreich"] == "finished_at"
    assert TIMESTAMP_FIELD["nicht_reparierbar"] == "finished_at"
    assert TIMESTAMP_FIELD["abgeholt"] == "picked_up_at"
    assert "offen" not in TIMESTAMP_FIELD


def test_can_transition_offen_to_in_arbeit():
    assert can_transition("offen", "in_arbeit") is True


def test_can_transition_offen_to_abgeholt():
    assert can_transition("offen", "abgeholt") is False


def test_can_transition_in_arbeit_to_erfolgreich():
    assert can_transition("in_arbeit", "erfolgreich") is True


def test_can_transition_erfolgreich_to_offen():
    assert can_transition("erfolgreich", "offen") is False


def test_can_transition_abgeholt_to_anything():
    for new_status in ("offen", "in_arbeit", "erfolgreich", "nicht_reparierbar", "abgeholt"):
        assert can_transition("abgeholt", new_status) is False


def test_can_transition_unknown_old_status():
    assert can_transition("quatsch", "offen") is False


# ---------- POST /api/tickets (Pflicht-Waiver) ----------

def test_post_ticket_without_waiver(app_client):
    device_id = create_device(app_client)
    resp = app_client.post(
        "/api/tickets", json={"device_id": device_id, "fault_description": "Kaputt"}
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == (
        "Haftungsausschluss muss akzeptiert und unterschrieben werden"
    )


def test_post_ticket_waiver_not_accepted(app_client):
    device_id = create_device(app_client)
    resp = app_client.post(
        "/api/tickets",
        json={"device_id": device_id, "fault_description": "Kaputt", "waiver": make_waiver(accepted=False)},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Haftungsausschluss muss akzeptiert werden"


def test_post_ticket_invalid_signature_data_url(app_client):
    device_id = create_device(app_client)
    resp = app_client.post(
        "/api/tickets",
        json={
            "device_id": device_id,
            "fault_description": "Kaputt",
            "waiver": make_waiver(signature_data_url="data:image/png;base64,@@@kein-base64@@@"),
        },
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]


def test_post_ticket_valid_creates_waiver_and_signature(app_client, tmp_path):
    device_id = create_device(app_client)
    resp = app_client.post(
        "/api/tickets",
        json={
            "device_id": device_id,
            "fault_description": "Kaputt",
            "assignee": "Anna",
            "waiver": make_waiver(),
        },
    )
    assert resp.status_code == 201
    ticket = resp.get_json()
    assert ticket["id"] >= 1
    assert ticket["status"] == "offen"
    assert ticket["device_id"] == device_id
    assert ticket["fault_description"] == "Kaputt"
    assert ticket["assignee"] == "Anna"
    assert ticket["created_at"]

    db_path = os.path.join(str(tmp_path), "repair.db")
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT ticket_id, waiver_version, signed_name, accepted, signature_path"
            " FROM waivers WHERE ticket_id = ?",
            (ticket["id"],),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == ticket["id"]
    assert row[1] == "2026-08-28"
    assert row[2] == "Max Mustermann"
    assert row[3] == 1
    sig_rel = row[4]
    assert sig_rel and sig_rel.startswith("signatures/")
    assert os.path.isfile(os.path.join(str(tmp_path), sig_rel))


def test_post_ticket_unknown_device_404(app_client):
    resp = app_client.post(
        "/api/tickets",
        json={"device_id": 9999, "fault_description": "Kaputt", "waiver": make_waiver()},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Gerät nicht gefunden"


def test_post_ticket_missing_fault_description(app_client):
    device_id = create_device(app_client)
    for desc in (None, "", "   "):
        resp = app_client.post(
            "/api/tickets",
            json={"device_id": device_id, "fault_description": desc, "waiver": make_waiver()},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Fehlerbeschreibung ist erforderlich"


# ---------- Statuswechsel via API ----------

def test_status_change_offen_to_in_arbeit_sets_started_at(app_client):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    resp = app_client.post(f"/api/tickets/{ticket['id']}/status", json={"status": "in_arbeit"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "in_arbeit"
    assert data["started_at"] is not None
    assert data["device_name"]


def test_status_change_offen_to_abgeholt_forbidden(app_client):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    resp = app_client.post(f"/api/tickets/{ticket['id']}/status", json={"status": "abgeholt"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Übergang von 'offen' nach 'abgeholt' ist nicht erlaubt"


def test_status_change_in_arbeit_back_to_offen(app_client):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    app_client.post(f"/api/tickets/{ticket['id']}/status", json={"status": "in_arbeit"})
    resp = app_client.post(f"/api/tickets/{ticket['id']}/status", json={"status": "offen"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "offen"


def test_status_change_unknown_ticket_404(app_client):
    resp = app_client.post("/api/tickets/9999/status", json={"status": "in_arbeit"})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Laufzettel nicht gefunden"


def test_status_change_unknown_status_value(app_client):
    device_id = create_device(app_client)
    ticket = create_ticket(app_client, device_id)
    resp = app_client.post(f"/api/tickets/{ticket['id']}/status", json={"status": "quatsch"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]


# ---------- GET: Liste, Detail, Board ----------

def test_get_ticket_by_id_joins_device_name(app_client):
    device_id = create_device(app_client, "Bohrmaschine")
    ticket = create_ticket(app_client, device_id)
    resp = app_client.get(f"/api/tickets/{ticket['id']}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == ticket["id"]
    assert data["device_name"] == "Bohrmaschine"


def test_get_ticket_404(app_client):
    resp = app_client.get("/api/tickets/9999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Laufzettel nicht gefunden"


def test_get_tickets_filters_by_status(app_client):
    device_id = create_device(app_client)
    t1 = create_ticket(app_client, device_id)
    t2 = create_ticket(app_client, device_id)
    app_client.post(f"/api/tickets/{t2['id']}/status", json={"status": "in_arbeit"})

    resp = app_client.get("/api/tickets")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2

    resp = app_client.get("/api/tickets?status=offen")
    assert [t["id"] for t in resp.get_json()] == [t1["id"]]

    resp = app_client.get("/api/tickets?status=in_arbeit")
    assert [t["id"] for t in resp.get_json()] == [t2["id"]]

    resp = app_client.get("/api/tickets?status=unsinn")
    assert resp.status_code == 400
    assert "offen" in resp.get_json()["error"]


def test_board_groups_by_status(app_client):
    device_id = create_device(app_client)
    t1 = create_ticket(app_client, device_id, fault_description="Radio kaputt")
    t2 = create_ticket(app_client, device_id, fault_description="Toaster defekt", assignee="Anna")
    app_client.post(f"/api/tickets/{t2['id']}/status", json={"status": "in_arbeit"})

    resp = app_client.get("/api/board")
    assert resp.status_code == 200
    board = resp.get_json()
    assert set(board.keys()) == {"offen", "in_arbeit", "erfolgreich", "nicht_reparierbar", "abgeholt"}
    assert [t["id"] for t in board["offen"]] == [t1["id"]]
    assert [t["id"] for t in board["in_arbeit"]] == [t2["id"]]
    for status in ("erfolgreich", "nicht_reparierbar", "abgeholt"):
        assert board[status] == []
    assert board["in_arbeit"][0]["device_name"]
    assert board["in_arbeit"][0]["fault_description"] == "Toaster defekt"
    assert board["in_arbeit"][0]["assignee"] == "Anna"
    assert board["in_arbeit"][0]["created_at"]