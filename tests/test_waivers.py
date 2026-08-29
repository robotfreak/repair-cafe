"""Tests für Haftungsausschluss-Modul (Task 3b)."""
import base64
import sqlite3

import pytest

import app.waivers as waivers

PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
PNG_DATA_URL = "data:image/png;base64," + PNG_B64


def make_waiver(**overrides):
    w = {"signed_name": "Max Mustermann", "accepted": True, "signature_data_url": PNG_DATA_URL}
    w.update(overrides)
    return w


def seed_ticket_with_waiver(tmp_path, signature_path="signatures/test.png"):
    """Legt Gerät + Laufzettel + Waiver direkt in der repair.db des app_client an."""
    conn = sqlite3.connect(str(tmp_path / "repair.db"))
    try:
        cur = conn.execute("INSERT INTO devices (name) VALUES (?)", ("Testgerät",))
        device_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO tickets (device_id, fault_description) VALUES (?, ?)",
            (device_id, "Defekt"),
        )
        ticket_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO waivers (ticket_id, waiver_version, signed_name, accepted, signature_path)"
            " VALUES (?, ?, ?, 1, ?)",
            (ticket_id, "2026-08-28", "Max Mustermann", signature_path),
        )
        waiver_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    return ticket_id, waiver_id


# ---------- validate_waiver (reine Funktion) ----------

def test_validate_waiver_ok():
    ok, msg, cleaned = waivers.validate_waiver(make_waiver())
    assert ok is True
    assert msg is None
    assert cleaned["signed_name"] == "Max Mustermann"
    assert cleaned["accepted"] is True
    assert cleaned["signature_data_url"] == PNG_DATA_URL


def test_validate_waiver_not_accepted():
    ok, msg, cleaned = waivers.validate_waiver(make_waiver(accepted=False))
    assert ok is False
    assert msg
    assert cleaned is None


def test_validate_waiver_blank_name():
    for name in ["", "   "]:
        ok, msg, cleaned = waivers.validate_waiver(make_waiver(signed_name=name))
        assert ok is False
        assert msg
        assert cleaned is None


def test_validate_waiver_name_too_long():
    ok, msg, cleaned = waivers.validate_waiver(make_waiver(signed_name="x" * 101))
    assert ok is False
    assert msg


def test_validate_waiver_wrong_prefix():
    ok, msg, cleaned = waivers.validate_waiver(
        make_waiver(signature_data_url="data:image/jpeg;base64," + PNG_B64)
    )
    assert ok is False
    assert msg
    assert cleaned is None


def test_validate_waiver_missing_returns_special_message():
    ok, msg, cleaned = waivers.validate_waiver(None)
    assert ok is False
    assert msg == "Haftungsausschluss muss akzeptiert und unterschrieben werden"
    assert cleaned is None


# ---------- save_signature (reine Funktion) ----------

def test_save_signature_writes_file(tmp_path):
    rel_path = waivers.save_signature(str(tmp_path), 7, PNG_DATA_URL)
    assert rel_path.startswith("signatures/waiver-7-")
    assert rel_path.endswith(".png")
    full = tmp_path / rel_path
    assert full.is_file()
    assert full.read_bytes() == base64.b64decode(PNG_B64)


def test_save_signature_too_large(tmp_path):
    oversized = "data:image/png;base64," + base64.b64encode(b"x" * 500_001).decode()
    with pytest.raises(ValueError):
        waivers.save_signature(str(tmp_path), 1, oversized)


def test_save_signature_invalid_data_url(tmp_path):
    with pytest.raises(ValueError):
        waivers.save_signature(str(tmp_path), 1, "data:image/jpeg;base64," + PNG_B64)
    with pytest.raises(ValueError):
        waivers.save_signature(str(tmp_path), 1, "data:image/png;base64,@@@kein-base64@@@")


def test_max_signature_bytes_constant():
    assert waivers.MAX_SIGNATURE_BYTES == 500_000


# ---------- Blueprint-Routen ----------

def test_get_waiver_text(app_client):
    resp = app_client.get("/api/waiver")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["version"] == "2026-08-28"
    assert "Haftungsausschluss – Repair-Café" in data["text"]


def test_ticket_waiver_404_without_waiver(app_client):
    resp = app_client.get("/api/tickets/1/waiver")
    assert resp.status_code == 404


def test_ticket_waiver_200_with_metadata(app_client, tmp_path):
    # Signaturdatei testweise anlegen
    sig_dir = tmp_path / "signatures"
    sig_dir.mkdir(exist_ok=True)
    (sig_dir / "test.png").write_bytes(base64.b64decode(PNG_B64))

    ticket_id, waiver_id = seed_ticket_with_waiver(tmp_path)

    resp = app_client.get(f"/api/tickets/{ticket_id}/waiver")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["signed_name"] == "Max Mustermann"
    assert data["waiver_version"] == "2026-08-28"
    assert data["signed_at"]
    assert data["signature_url"] == f"/api/waivers/{waiver_id}/signature"


def test_signature_stream_returns_png(app_client, tmp_path):
    sig_dir = tmp_path / "signatures"
    sig_dir.mkdir(exist_ok=True)
    (sig_dir / "test.png").write_bytes(base64.b64decode(PNG_B64))

    _, waiver_id = seed_ticket_with_waiver(tmp_path)

    resp = app_client.get(f"/api/waivers/{waiver_id}/signature")
    assert resp.status_code == 200
    assert "image/png" in resp.headers["Content-Type"]
    assert resp.data == base64.b64decode(PNG_B64)


def test_signature_stream_404_without_path(app_client, tmp_path):
    ticket_id, waiver_id = seed_ticket_with_waiver(tmp_path, signature_path=None)
    resp = app_client.get(f"/api/waivers/{waiver_id}/signature")
    assert resp.status_code == 404


def test_signature_stream_blocks_path_traversal(app_client, tmp_path):
    _, waiver_id = seed_ticket_with_waiver(tmp_path, signature_path="../../etc/passwd")
    resp = app_client.get(f"/api/waivers/{waiver_id}/signature")
    assert resp.status_code == 404


def test_signature_stream_404_unknown_id(app_client):
    resp = app_client.get("/api/waivers/9999/signature")
    assert resp.status_code == 404