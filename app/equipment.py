"""VDE/DGUV-Geräteprüfung: Checkliste + Speicherung der Messwerte am Ticket."""
import json

import flask

from app.db import get_request_db
from app.dguv import PROTECTION_CLASSES, checks_for, evaluate

bp = flask.Blueprint("equipment", __name__)

TESTER_MAX = 100
NOTES_MAX = 1000


def _device_of_ticket(conn, ticket_id):
    return conn.execute(
        "SELECT d.* FROM tickets t JOIN devices d ON d.id = t.device_id"
        " WHERE t.id = ?",
        (ticket_id,),
    ).fetchone()


def _row_to_dict(row):
    data = dict(row)
    data["measurements"] = json.loads(data["measurements"])
    return data


@bp.route("/api/dguv/checks", methods=["GET"])
def all_checks():
    """Vollständiger Katalog aller drei Schutzklassen (Referenz/Dokumentation).
    
    Seit 2026-09-05: use_vde_conform=False (UNI-T UT-501 Isolationsprüfung,
    nicht VDE-konform aber für Repair-Café ausreichend).
    """
    return {cls: checks_for(cls, use_vde_conform=False) for cls in PROTECTION_CLASSES}


# ---------- Prüfgeräte (Messmittel) ----------

NAME_MAX = 200
SERIAL_MAX = 100
CAL_MAX = 20      # z. B. '2027-05-31'
TD_NOTES_MAX = 500


@bp.route("/api/test-devices", methods=["GET"])
def list_test_devices():
    conn = get_request_db(flask.current_app)
    rows = conn.execute(
        "SELECT id, name, serial_number, calibration_until, notes, archived"
        " FROM test_devices WHERE archived = 0 ORDER BY name"
    ).fetchall()
    return {"test_devices": [dict(r) for r in rows]}


@bp.route("/api/test-devices", methods=["POST"])
def create_test_device():
    conn = get_request_db(flask.current_app)
    payload = flask.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "JSON-Body erforderlich"}, 400
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"error": "Name ist erforderlich"}, 400
    name = name.strip()
    if len(name) > NAME_MAX:
        return {"error": f"Name darf höchstens {NAME_MAX} Zeichen lang sein"}, 400

    serial = payload.get("serial_number")
    if serial is not None and not isinstance(serial, str):
        return {"error": "serial_number muss ein Textfeld sein"}, 400
    serial = (serial or "").strip() or None
    if serial and len(serial) > SERIAL_MAX:
        return {"error": f"serial_number darf höchstens {SERIAL_MAX} Zeichen lang sein"}, 400

    cal = payload.get("calibration_until")
    if cal is not None and not isinstance(cal, str):
        return {"error": "calibration_until muss ein Textfeld (Datum) sein"}, 400
    cal = (cal or "").strip() or None
    if cal and len(cal) > CAL_MAX:
        return {"error": f"calibration_until darf höchstens {CAL_MAX} Zeichen lang sein"}, 400

    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, str):
        return {"error": "notes muss ein Textfeld sein"}, 400
    notes = (notes or "").strip() or None
    if notes and len(notes) > TD_NOTES_MAX:
        return {"error": f"notes darf höchstens {TD_NOTES_MAX} Zeichen lang sein"}, 400

    cur = conn.execute(
        "INSERT INTO test_devices (name, serial_number, calibration_until, notes)"
        " VALUES (?, ?, ?, ?)",
        (name, serial, cal, notes),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM test_devices WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row), 201


@bp.route("/api/tickets/<int:ticket_id>/equipment-test/checks", methods=["GET"])
def checks_for_ticket(ticket_id):
    """Checkliste passend zur Schutzklasse des Geräts am Laufzettel.
    
    Seit 2026-09-05: use_vde_conform=False (UNI-T UT-501 statt VDE).
    """
    conn = get_request_db(flask.current_app)
    if conn.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
        return {"error": "Laufzettel nicht gefunden"}, 404
    device = _device_of_ticket(conn, ticket_id)
    if device is None or not device["schutzklasse"]:
        return {"error": "Gerät hat keine Schutzklasse — bitte im Geräte-Tab hinterlegen"}, 409
    return {
        "protection_class": device["schutzklasse"],
        "heating_kw": device["heating_kw"],
        "checks": checks_for(device["schutzklasse"], device["heating_kw"], use_vde_conform=False),
    }


@bp.route("/api/tickets/<int:ticket_id>/equipment-test", methods=["GET"])
def get_test(ticket_id):
    conn = get_request_db(flask.current_app)
    row = conn.execute(
        "SELECT * FROM equipment_tests WHERE ticket_id = ?", (ticket_id,)
    ).fetchone()
    if row is None:
        return {"error": "Keine Prüfung vorhanden"}, 404
    return _row_to_dict(row)


@bp.route("/api/tickets/<int:ticket_id>/equipment-test", methods=["POST"])
def save_test(ticket_id):
    conn = get_request_db(flask.current_app)
    if conn.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
        return {"error": "Laufzettel nicht gefunden"}, 404
    device = _device_of_ticket(conn, ticket_id)
    if device is None or not device["schutzklasse"]:
        return {"error": "Gerät hat keine Schutzklasse — bitte im Geräte-Tab hinterlegen"}, 409

    payload = flask.request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("measurements"), dict):
        return {"error": "Messwerte (measurements) sind erforderlich"}, 400
    values = payload["measurements"]

    tester = payload.get("tester")
    if tester is not None:
        if not isinstance(tester, str):
            return {"error": "tester muss ein Textfeld sein"}, 400
        tester = tester.strip() or None
        if tester and len(tester) > TESTER_MAX:
            return {"error": f"tester darf höchstens {TESTER_MAX} Zeichen lang sein"}, 400

    notes = payload.get("notes")
    if notes is not None:
        if not isinstance(notes, str):
            return {"error": "notes muss ein Textfeld sein"}, 400
        notes = notes.strip() or None
        if notes and len(notes) > NOTES_MAX:
            return {"error": f"notes darf höchstens {NOTES_MAX} Zeichen lang sein"}, 400

    # Prüfgerät: entweder vorhandene ID oder Snapshot-Text (freies Feld).
    test_device = payload.get("test_device")
    test_device_id = None
    test_device_snapshot = None
    if test_device is not None:
        if isinstance(test_device, dict):
            td = test_device
            td_id = td.get("id")
            td_row = None
            # String-ID = virtuelles Gerät (z.B. 'uni-t-ut501'), kein DB-Lookup
            if td_id is not None and not isinstance(td_id, int):
                # Virtuelles Gerät (String-ID), kein DB-Lookup nötig
                snap_name = td.get("name") or str(td_id)
                if not isinstance(snap_name, str) or not snap_name.strip():
                    return {"error": "test_device.name ist erforderlich (Messgerät)"}, 400
                snap_serial = td.get("serial_number")
                snap_cal = td.get("calibration_until")
                test_device_snapshot = json.dumps({
                    "name": snap_name.strip(),
                    "serial_number": (snap_serial or "").strip() or None,
                    "calibration_until": (snap_cal or "").strip() or None,
                }, ensure_ascii=False)
                test_device_id = None
            elif td_id is not None:
                # Echte DB-ID (int)
                if not isinstance(td_id, int):
                    return {"error": "test_device.id muss eine Zahl sein"}, 400
                td_row = conn.execute(
                    "SELECT * FROM test_devices WHERE id = ? AND archived = 0", (td_id,)
                ).fetchone()
                if td_row is None:
                    return {"error": "Prüfgerät nicht gefunden"}, 404
                test_device_id = td_row["id"]
                snap_name = td.get("name") or (td_row["name"] if td_row else None)
                if not isinstance(snap_name, str) or not snap_name.strip():
                    return {"error": "test_device.name ist erforderlich (Messgerät)"}, 400
                snap_serial = td.get("serial_number") or (td_row["serial_number"] if td_row else None)
                snap_cal = td.get("calibration_until") or (td_row["calibration_until"] if td_row else None)
                test_device_snapshot = json.dumps({
                    "name": snap_name.strip(),
                    "serial_number": (snap_serial or "").strip() or None,
                    "calibration_until": (snap_cal or "").strip() or None,
                }, ensure_ascii=False)
        elif isinstance(test_device, str):
            if not test_device.strip():
                return {"error": "test_device darf nicht leer sein"}, 400
            if len(test_device) > 300:
                return {"error": "test_device darf höchstens 300 Zeichen lang sein"}, 400
            test_device_snapshot = json.dumps({"name": test_device.strip()}, ensure_ascii=False)
            test_device_id = None
        else:
            return {"error": "test_device muss ein Objekt oder Text sein"}, 400

    # Seit 2026-09-05: use_vde_conform=False (UNI-T UT-501 statt VDE)
    checks = checks_for(device["schutzklasse"], device["heating_kw"], use_vde_conform=False)
    measurements = {}
    problems = []
    all_ok = True
    for check in checks:
        # UI sendet Labels als Schlüssel, API-Tests die internen Keys — beides akzeptieren.
        raw = values.get(check["key"])
        if raw is None or raw == "":
            raw = values.get(check["label"])
        if raw is None or raw == "":
            problems.append(f"Messwert fehlt: {check['label']}")
            continue
        ok, message = evaluate(check, raw)
        if not ok:
            all_ok = False
        measurements[check["key"]] = {
            "label": check["label"],
            "value": raw if check["direction"] == "bool" else float(raw),
            "unit": check["unit"],
            "ok": 1 if ok else 0,
            "message": message,
        }
    # Überzählige Schlüssel werden ignoriert (defense in depth: nur Katalog-Keys gespeichert)
    if problems:
        return {"error": "; ".join(problems)}, 400

    verdict = "bestanden" if all_ok else "nicht_bestanden"
    conn.execute(
        "INSERT INTO equipment_tests (ticket_id, protection_class, heating_kw,"
        " measurements, verdict, tester, notes, test_device_id, test_device_snapshot)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(ticket_id) DO UPDATE SET"
        " protection_class=excluded.protection_class,"
        " heating_kw=excluded.heating_kw,"
        " measurements=excluded.measurements,"
        " verdict=excluded.verdict, tester=excluded.tester, notes=excluded.notes,"
        " test_device_id=excluded.test_device_id,"
        " test_device_snapshot=excluded.test_device_snapshot,"
        " created_at=datetime('now')",
        (ticket_id, device["schutzklasse"], device["heating_kw"],
         json.dumps(measurements, ensure_ascii=False), verdict, tester, notes,
         test_device_id, test_device_snapshot),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM equipment_tests WHERE ticket_id = ?", (ticket_id,)
    ).fetchone()
    return _row_to_dict(row), 201