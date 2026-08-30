"""Tests: Prüfgeräte (Messmittel) für VDE-Prüfungen — CRUD + Verknüpfung."""
import json

import pytest

from tests.test_journal_edit import make_ticket as _mk_tid


def make_ticket(app_client, name="Prüfgerät-Test"):
    """Liefert (ticket_dict) inkl. device_id (make_ticket gibt nur int zurück)."""
    tid = _mk_tid(app_client, name)
    return app_client.get(f"/api/tickets/{tid}").get_json()


@pytest.fixture()
def test_device(app_client):
    resp = app_client.post("/api/test-devices", json={
        "name": "METRAHIT ENERGY",
        "serial_number": "A1B2C3D4",
        "calibration_until": "2027-05-31",
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_create_und_list_test_devices(app_client, test_device):
    lst = app_client.get("/api/test-devices").get_json()["test_devices"]
    assert len(lst) == 1
    assert lst[0]["name"] == "METRAHIT ENERGY"
    assert lst[0]["serial_number"] == "A1B2C3D4"
    assert lst[0]["calibration_until"] == "2027-05-31"
    assert lst[0]["archived"] == 0


def test_create_ohne_name_400(app_client):
    resp = app_client.post("/api/test-devices", json={"serial_number": "x"})
    assert resp.status_code == 400
    assert "Name" in resp.get_json()["error"]


def test_create_leerer_name_400(app_client):
    resp = app_client.post("/api/test-devices", json={"name": "   "})
    assert resp.status_code == 400


def test_create_zu_lange_felder_400(app_client):
    resp = app_client.post("/api/test-devices", json={
        "name": "x" * 201,
    })
    assert resp.status_code == 400
    resp = app_client.post("/api/test-devices", json={
        "name": "ok", "serial_number": "x" * 101,
    })
    assert resp.status_code == 400


def test_pruefung_mit_test_device_id_snapshot(app_client, test_device):
    """Speichern mit Prüfgerät-ID → Snapshot aus DB-Stand in der Prüfung."""
    tid = make_ticket(app_client)
    app_client.patch(f"/api/devices/{tid['device_id']}", json={"schutzklasse": "II"})
    payload = {
        "measurements": {
            "besichtigung": "ok",
            "isolation": "3",
            "funktion": "ok",
            "beruehrungsstrom": "0.2",
        },
        "tester": "Peter",
        "test_device": {"id": test_device["id"]},
    }
    resp = app_client.post(f"/api/tickets/{tid['id']}/equipment-test", json=payload)
    assert resp.status_code == 201, resp.get_json()
    saved = app_client.get(f"/api/tickets/{tid['id']}/equipment-test").get_json()
    assert saved["test_device_id"] == test_device["id"]
    snap = json.loads(saved["test_device_snapshot"])
    assert snap["name"] == "METRAHIT ENERGY"
    assert snap["serial_number"] == "A1B2C3D4"
    assert snap["calibration_until"] == "2027-05-31"


def test_pruefung_mit_freiem_text_ohne_db_eintrag(app_client):
    """Ohne DB-Eintrage: freier Text als Prüfgerät → Snapshot nur mit name."""
    tid = make_ticket(app_client)
    app_client.patch(f"/api/devices/{tid['device_id']}", json={"schutzklasse": "I"})
    payload = {
        "measurements": {
            "besichtigung": "ok",
            "schutzleiter": "0.1",
            "isolation": "2",
            "schutzleiterstrom": "1",
            "beruehrungsstrom": "0.2",
            "funktion": "ok",
        },
        "tester": "Peter",
        "test_device": "Benning DIN 70542 (Nr. 123)",
    }
    resp = app_client.post(f"/api/tickets/{tid['id']}/equipment-test", json=payload)
    assert resp.status_code == 201, resp.get_json()
    saved = app_client.get(f"/api/tickets/{tid['id']}/equipment-test").get_json()
    assert saved["test_device_id"] is None
    snap = json.loads(saved["test_device_snapshot"])
    assert snap["name"] == "Benning DIN 70542 (Nr. 123)"
    assert snap.get("serial_number") is None


def test_pruefung_ohne_test_device_snapshot_leer(app_client):
    """Rückwärtskompatibel: ohne test_device → None (kein Fehler)."""
    tid = make_ticket(app_client)
    app_client.patch(f"/api/devices/{tid['device_id']}", json={"schutzklasse": "III"})
    payload = {
        "measurements": {"besichtigung": "ok", "isolation": "0.5", "funktion": "ok"},
        "tester": "Peter",
    }
    resp = app_client.post(f"/api/tickets/{tid['id']}/equipment-test", json=payload)
    assert resp.status_code == 201, resp.get_json()
    saved = app_client.get(f"/api/tickets/{tid['id']}/equipment-test").get_json()
    assert saved["test_device_id"] is None
    assert saved["test_device_snapshot"] is None


def test_pruefung_unbekannte_test_device_id_404(app_client, test_device):
    tid = make_ticket(app_client)
    app_client.patch(f"/api/devices/{tid['device_id']}", json={"schutzklasse": "II"})
    payload = {
        "measurements": {"isolation": "3", "beruehrungsstrom": "0.2"},
        "test_device": {"id": 99999},
    }
    resp = app_client.post(f"/api/tickets/{tid['id']}/equipment-test", json=payload)
    assert resp.status_code == 404
    assert "Prüfgerät nicht gefunden" in resp.get_json()["error"]


def test_leeres_test_device_objekt_400(app_client):
    tid = make_ticket(app_client)
    app_client.patch(f"/api/devices/{tid['device_id']}", json={"schutzklasse": "I"})
    payload = {
        "measurements": {"besichtigung": "ok", "schutzleiter": "0.1",
                         "isolation": "2", "schutzleiterstrom": "1",
                         "beruehrungsstrom": "0.2", "funktion": "ok"},
        "test_device": {},
    }
    resp = app_client.post(f"/api/tickets/{tid['id']}/equipment-test", json=payload)
    assert resp.status_code == 400
    assert "test_device.name ist erforderlich" in resp.get_json()["error"]