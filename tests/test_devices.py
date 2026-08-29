"""Tests für Geräte-CRUD (Task 3)."""
import sqlite3


def test_create_and_get_roundtrip(app_client):
    resp = app_client.post("/api/devices", json={
        "name": "Bohrmaschine",
        "category": "Werkzeug",
        "manufacturer": "Bosch",
        "model": "PSB 700",
        "serial_number": "SN-12345",
        "owner_name": "Max Mustermann",
        "owner_contact": "max@example.org",
        "accessories": "Bohrer-Satz, Koffer",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert isinstance(data["id"], int)
    assert data["name"] == "Bohrmaschine"
    assert data["manufacturer"] == "Bosch"
    assert data["category"] == "Werkzeug"
    assert data["model"] == "PSB 700"
    assert data["serial_number"] == "SN-12345"
    assert data["owner_name"] == "Max Mustermann"
    assert data["owner_contact"] == "max@example.org"
    assert data["accessories"] == "Bohrer-Satz, Koffer"
    assert data["created_at"]

    resp2 = app_client.get(f"/api/devices/{data['id']}")
    assert resp2.status_code == 200
    got = resp2.get_json()
    assert got["id"] == data["id"]
    assert got["manufacturer"] == "Bosch"
    assert got["created_at"] == data["created_at"]


def test_post_without_name_400(app_client):
    resp = app_client.post("/api/devices", json={"manufacturer": "Bosch"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Name ist erforderlich"


def test_post_empty_and_whitespace_name_400(app_client):
    for name in ["", "   "]:
        resp = app_client.post("/api/devices", json={"name": name})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Name ist erforderlich"


def test_post_name_too_long_400(app_client):
    resp = app_client.post("/api/devices", json={"name": "x" * 201})
    assert resp.status_code == 400


def test_post_field_too_long_400(app_client):
    resp = app_client.post("/api/devices", json={"name": "Ding", "category": "y" * 501})
    assert resp.status_code == 400


def test_list_q_filter(app_client):
    app_client.post("/api/devices", json={"name": "Bohrmaschine", "manufacturer": "Bosch"})
    app_client.post("/api/devices", json={"name": "Nähmaschine", "manufacturer": "Pfaff"})

    resp = app_client.get("/api/devices")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2

    resp = app_client.get("/api/devices?q=bosch")
    assert resp.status_code == 200
    items = resp.get_json()
    assert len(items) == 1
    assert items[0]["name"] == "Bohrmaschine"
    assert items[0]["manufacturer"] == "Bosch"


def test_patch_changes_manufacturer(app_client):
    resp = app_client.post("/api/devices", json={"name": "Bohrmaschine", "manufacturer": "Bosch"})
    device_id = resp.get_json()["id"]

    resp = app_client.patch(f"/api/devices/{device_id}", json={"manufacturer": "Makita"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["manufacturer"] == "Makita"
    assert data["name"] == "Bohrmaschine"

    resp = app_client.get(f"/api/devices/{device_id}")
    assert resp.get_json()["manufacturer"] == "Makita"


def test_patch_empty_name_400(app_client):
    resp = app_client.post("/api/devices", json={"name": "Bohrmaschine"})
    device_id = resp.get_json()["id"]
    resp = app_client.patch(f"/api/devices/{device_id}", json={"name": "  "})
    assert resp.status_code == 400


def test_delete_without_tickets(app_client):
    resp = app_client.post("/api/devices", json={"name": "Radio"})
    device_id = resp.get_json()["id"]

    resp = app_client.delete(f"/api/devices/{device_id}")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}

    resp = app_client.get(f"/api/devices/{device_id}")
    assert resp.status_code == 404


def test_delete_with_ticket_409(app_client, tmp_path):
    resp = app_client.post("/api/devices", json={"name": "Bohrmaschine"})
    device_id = resp.get_json()["id"]

    # Laufzettel direkt in dieselbe repair.db einfügen (app_client nutzt data_dir=tmp_path)
    conn = sqlite3.connect(str(tmp_path / "repair.db"))
    try:
        conn.execute(
            "INSERT INTO tickets (device_id, fault_description) VALUES (?, ?)",
            (device_id, "Läuft nicht mehr"),
        )
        conn.commit()
    finally:
        conn.close()

    resp = app_client.delete(f"/api/devices/{device_id}")
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "Gerät hat Laufzettel und kann nicht gelöscht werden"


def test_get_unknown_id_404(app_client):
    resp = app_client.get("/api/devices/9999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Gerät nicht gefunden"