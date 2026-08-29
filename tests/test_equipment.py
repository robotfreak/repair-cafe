"""Tests für Schutzklasse + VDE/DGUV-Geräteprüfung (Equipment-Checks)."""
import sqlite3

import pytest

from app.dguv import checks_for, evaluate


# ---------- Katalog (reine Funktionen) ----------

def test_schutzklasse_I_checkliste():
    checks = checks_for("I")
    keys = [c["key"] for c in checks]
    assert keys == [
        "besichtigung", "schutzleiter", "isolation",
        "schutzleiterstrom", "beruehrungsstrom", "funktion",
    ]
    sl = next(c for c in checks if c["key"] == "schutzleiter")
    assert sl["direction"] == "max" and sl["limit"] == 0.3 and sl["unit"] == "Ω"
    iso = next(c for c in checks if c["key"] == "isolation")
    assert iso["direction"] == "min" and iso["limit"] == 1.0 and iso["unit"] == "MΩ"
    sls = next(c for c in checks if c["key"] == "schutzleiterstrom")
    assert sls["limit"] == 3.5 and sls["unit"] == "mA"


def test_schutzklasse_I_mit_heizelement_grenzwerte_geschaerft():
    checks = checks_for("I", heating_kw=2.0)
    iso = next(c for c in checks if c["key"] == "isolation")
    assert iso["limit"] == 0.3
    sls = next(c for c in checks if c["key"] == "schutzleiterstrom")
    assert sls["limit"] == 2.0          # 1 mA/kW × 2 kW
    assert "max. 10" in (sls["hint"] or "")


def test_schutzklasse_I_heizelement_cap_10mA():
    sls = next(c for c in checks_for("I", heating_kw=25.0)
               if c["key"] == "schutzleiterstrom")
    assert sls["limit"] == 10.0


def test_schutzklasse_II_und_III_checkliste():
    ii = checks_for("II")
    assert [c["key"] for c in ii] == ["besichtigung", "isolation", "beruehrungsstrom", "funktion"]
    assert next(c for c in ii if c["key"] == "isolation")["limit"] == 2.0

    iii = checks_for("III")
    assert [c["key"] for c in iii] == ["besichtigung", "isolation", "funktion"]
    assert next(c for c in iii if c["key"] == "isolation")["limit"] == 0.25


def test_schutzklasse_III_hat_keinen_beruehrungsstrom():
    assert all(c["key"] != "beruehrungsstrom" for c in checks_for("III"))
    assert all(c["key"] != "schutzleiter" for c in checks_for("III"))


def test_unbekannte_schutzklasse_raises():
    with pytest.raises(ValueError):
        checks_for("IV")


# ---------- Bewertung ----------

def test_evaluate_max_ok_und_fail():
    check = {"direction": "max", "limit": 0.3, "unit": "Ω", "label": "SL", "key": "x"}
    assert evaluate(check, "0.28") == (True, None)
    ok, msg = evaluate(check, "0.4")
    assert not ok and "0,4" in msg.replace(".", ",") or "0.4" in msg


def test_evaluate_min_und_bool():
    check = {"direction": "min", "limit": 1.0, "unit": "MΩ", "label": "Iso", "key": "x"}
    assert evaluate(check, 2.5)[0] is True
    assert evaluate(check, 0.5)[0] is False
    bcheck = {"direction": "bool", "limit": None, "unit": None, "label": "Sicht", "key": "x"}
    assert evaluate(bcheck, "ok") == (True, None)
    assert evaluate(bcheck, "mangelhaft")[0] is False


def test_evaluate_ungueltige_werte():
    check = {"direction": "max", "limit": 3.5, "unit": "mA", "label": "SL", "key": "x"}
    assert evaluate(check, "abc")[0] is False
    assert evaluate(check, "-1")[0] is False
    assert evaluate(check, "")[0] is False


# ---------- Geräte-API: schutzklasse / heating_kw ----------

def test_device_schutzklasse_wird_normalisiert(app_client):
    resp = app_client.post("/api/devices", json={"name": "X", "schutzklasse": " ii "})
    assert resp.status_code == 201
    assert resp.get_json()["schutzklasse"] == "II"


def test_device_schutzklasse_invalid_400(app_client):
    for bad in ("IV", "1", True, []):
        resp = app_client.post("/api/devices", json={"name": "X", "schutzklasse": bad})
        assert resp.status_code == 400
        assert "schutzklasse" in resp.get_json()["error"]


def test_device_heating_kw_validierung(app_client):
    ok = app_client.post("/api/devices", json={"name": "Föhn", "schutzklasse": "I", "heating_kw": 2})
    assert ok.status_code == 201
    assert ok.get_json()["heating_kw"] == 2.0

    for bad in (0, -1, "2", True):
        resp = app_client.post("/api/devices", json={"name": "Y", "heating_kw": bad})
        assert resp.status_code == 400


def test_device_patch_schutzklasse(app_client):
    did = app_client.post("/api/devices", json={"name": "A"}).get_json()["id"]
    resp = app_client.patch(f"/api/devices/{did}", json={"schutzklasse": "iii"})
    assert resp.get_json()["schutzklasse"] == "III"


# ---------- Checkliste-Endpunkt ----------

def test_dguv_checks_katalog(app_client):
    resp = app_client.get("/api/dguv/checks")
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data.keys()) == {"I", "II", "III"}


def test_checks_409_ohne_schutzklasse(app_client):
    did = app_client.post("/api/devices", json={"name": "A"}).get_json()["id"]
    tid = app_client.post(
        "/api/tickets",
        json={"device_id": did, "fault_description": "kaputt",
              "waiver": {"signed_name": "M M", "accepted": True,
                         "signature_data_url": PNG}}).get_json()["id"]
    resp = app_client.get(f"/api/tickets/{tid}/equipment-test/checks")
    assert resp.status_code == 409
    assert "Schutzklasse" in resp.get_json()["error"]


def test_checks_passend_zur_schutzklasse(app_client):
    did = app_client.post(
        "/api/devices", json={"name": "Föhn", "schutzklasse": "I", "heating_kw": 2}
    ).get_json()["id"]
    tid = app_client.post(
        "/api/tickets",
        json={"device_id": did, "fault_description": "kaputt",
              "waiver": {"signed_name": "M M", "accepted": True,
                         "signature_data_url": PNG}}).get_json()["id"]
    resp = app_client.get(f"/api/tickets/{tid}/equipment-test/checks")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["protection_class"] == "I" and data["heating_kw"] == 2
    keys = [c["key"] for c in data["checks"]]
    assert "schutzleiter" in keys and "beruehrungsstrom" in keys


PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
       "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def make_ticket(client, device_payload, fault="kaputt"):
    did = client.post("/api/devices", json=device_payload).get_json()["id"]
    return client.post(
        "/api/tickets",
        json={"device_id": did, "fault_description": fault,
              "waiver": {"signed_name": "M M", "accepted": True,
                         "signature_data_url": PNG}}).get_json()["id"]


# ---------- Prüf-Speicherung ----------

def test_save_und_get_pruefung_sk1_bestanden(app_client):
    tid = make_ticket(app_client, {"name": "Föhn", "schutzklasse": "I", "heating_kw": 2})
    payload = {
        "measurements": {
            "besichtigung": "ok", "schutzleiter": 0.14, "isolation": 0.55,
            "schutzleiterstrom": 1.2, "beruehrungsstrom": 0.1, "funktion": "ok",
        },
        "tester": "Peter", "notes": "Alles im grünen Bereich",
    }
    resp = app_client.post(f"/api/tickets/{tid}/equipment-test", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["verdict"] == "bestanden"
    assert data["protection_class"] == "I"
    assert data["measurements"]["schutzleiter"] == {
        "label": "Schutzleiterwiderstand",
        "value": 0.14, "unit": "Ω", "ok": 1, "message": None}

    got = app_client.get(f"/api/tickets/{tid}/equipment-test")
    assert got.status_code == 200
    assert got.get_json()["tester"] == "Peter"


def test_pruefung_nicht_bestanden_bei_grenzwertverletzung(app_client):
    tid = make_ticket(app_client, {"name": "Werkzeug", "schutzklasse": "I"})
    resp = app_client.post(
        f"/api/tickets/{tid}/equipment-test",
        json={"measurements": {"besichtigung": "ok", "schutzleiter": 0.9,
                               "isolation": 5, "schutzleiterstrom": 1.0,
                               "beruehrungsstrom": 0.2, "funktion": "ok"}})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["verdict"] == "nicht_bestanden"
    assert "Grenzwert verletzt" in data["measurements"]["schutzleiter"]["message"]


def test_pruefung_fehlender_messwert_400(app_client):
    tid = make_ticket(app_client, {"name": "Radio", "schutzklasse": "II"})
    resp = app_client.post(
        f"/api/tickets/{tid}/equipment-test",
        json={"measurements": {"isolation": 3.0, "beruehrungsstrom": 0.2}})
    assert resp.status_code == 400
    assert "Messwert fehlt" in resp.get_json()["error"]
    assert "Besichtigung" in resp.get_json()["error"]


def test_pruefung_akzeptiert_labels_als_keys_uilaut(app_client):
    """Das UI sendet Messwerte mit dem deutschen Label als Schlüssel —
    regressionssicherstellen, dass das Backend das akzeptiert."""
    tid = make_ticket(app_client, {"name": "UI-Föhn", "schutzklasse": "I", "heating_kw": 2})
    payload = {
        "measurements": {
            "Besichtigung: Gehäuse, Leitung, Stecker, Schalter unbeschädigt": "ok",
            "Schutzleiterwiderstand": "0.14",
            "Isolationswiderstand (500 V DC)": "0.55",
            "Schutzleiterstrom": "1.2",
            "Berührungsstrom (nicht mit PE verbundene Teile)": "0.1",
            "Funktionsprüfung nach der Prüfung": "ok",
        },
        "tester": "Peter",
    }
    resp = app_client.post(f"/api/tickets/{tid}/equipment-test", json=payload)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["verdict"] == "bestanden"
    assert data["measurements"]["schutzleiter"]["value"] == 0.14


def test_pruefung_akzeptiert_keys_und_labels_gemischt(app_client):
    tid = make_ticket(app_client, {"name": "Mix", "schutzklasse": "III"})
    resp = app_client.post(
        f"/api/tickets/{tid}/equipment-test",
        json={"measurements": {"besichtigung": "ok",
                               "Isolationswiderstand (500 V DC)": 0.5,
                               "funktion": "ok"}, "tester": "X"})
    assert resp.status_code == 201
    assert resp.get_json()["verdict"] == "bestanden"


def test_pruefung_sk3_ohne_beruehrungsstrom(app_client):
    tid = make_ticket(app_client, {"name": "Netzteil", "schutzklasse": "III"})
    resp = app_client.post(
        f"/api/tickets/{tid}/equipment-test",
        json={"measurements": {"besichtigung": "ok", "isolation": 0.5, "funktion": "ok"}})
    assert resp.status_code == 201
    assert resp.get_json()["verdict"] == "bestanden"


def test_pruefung_ueberzaehlige_keys_ignoriert(app_client):
    tid = make_ticket(app_client, {"name": "Netzteil", "schutzklasse": "III"})
    resp = app_client.post(
        f"/api/tickets/{tid}/equipment-test",
        json={"measurements": {"besichtigung": "ok", "isolation": 0.5,
                               "funktion": "ok", "hack": "<script>"}})
    assert resp.status_code == 201
    assert "hack" not in resp.get_json()["measurements"]


def test_pruefung_upsert_eine_zeile_pro_ticket(app_client):
    tid = make_ticket(app_client, {"name": "Radio", "schutzklasse": "II"})
    first = app_client.post(
        f"/api/tickets/{tid}/equipment-test",
        json={"measurements": {"besichtigung": "ok", "isolation": 1.5,
                               "beruehrungsstrom": 0.2, "funktion": "ok"}})
    assert first.get_json()["verdict"] == "nicht_bestanden"  # 1.5 < 2.0 MΩ
    second = app_client.post(
        f"/api/tickets/{tid}/equipment-test",
        json={"measurements": {"besichtigung": "ok", "isolation": 3.0,
                               "beruehrungsstrom": 0.2, "funktion": "ok"}})
    assert second.get_json()["verdict"] == "bestanden"

    con = sqlite3.connect(app_client.application.config["DB_PATH"])
    n = con.execute("SELECT COUNT(*) FROM equipment_tests WHERE ticket_id = ?", (tid,)).fetchone()[0]
    con.close()
    assert n == 1


def test_pruefung_404_ohne_ticket(app_client):
    assert app_client.get("/api/tickets/999/equipment-test").status_code == 404
    assert app_client.post(
        "/api/tickets/999/equipment-test", json={"measurements": {}}).status_code == 404


# ---------- Migration bestehender DBs ----------

def test_migration_alte_db_bekommt_neue_spalten(tmp_path):
    from app.db import init_db
    p = str(tmp_path / "alt.db")
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE devices (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,"
                " category TEXT, manufacturer TEXT, model TEXT, serial_number TEXT,"
                " owner_name TEXT, owner_contact TEXT, accessories TEXT,"
                " created_at TEXT NOT NULL DEFAULT (datetime('now')))")
    con.execute("INSERT INTO devices (name) VALUES ('Altgerät')")
    con.commit()
    con.close()

    db = init_db(p)
    cols = {r[1] for r in db.execute("PRAGMA table_info(devices)")}
    assert {"schutzklasse", "heating_kw"} <= cols
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "equipment_tests" in tables
    row = db.execute("SELECT name, schutzklasse FROM devices").fetchone()
    assert row["name"] == "Altgerät" and row["schutzklasse"] is None