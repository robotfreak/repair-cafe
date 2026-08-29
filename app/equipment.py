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
    """Vollständiger Katalog aller drei Schutzklassen (Referenz/Dokumentation)."""
    return {cls: checks_for(cls) for cls in PROTECTION_CLASSES}


@bp.route("/api/tickets/<int:ticket_id>/equipment-test/checks", methods=["GET"])
def checks_for_ticket(ticket_id):
    """Checkliste passend zur Schutzklasse des Geräts am Laufzettel."""
    conn = get_request_db(flask.current_app)
    if conn.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
        return {"error": "Laufzettel nicht gefunden"}, 404
    device = _device_of_ticket(conn, ticket_id)
    if device is None or not device["schutzklasse"]:
        return {"error": "Gerät hat keine Schutzklasse — bitte im Geräte-Tab hinterlegen"}, 409
    return {
        "protection_class": device["schutzklasse"],
        "heating_kw": device["heating_kw"],
        "checks": checks_for(device["schutzklasse"], device["heating_kw"]),
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

    checks = checks_for(device["schutzklasse"], device["heating_kw"])
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
        " measurements, verdict, tester, notes)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(ticket_id) DO UPDATE SET"
        " protection_class=excluded.protection_class,"
        " heating_kw=excluded.heating_kw,"
        " measurements=excluded.measurements,"
        " verdict=excluded.verdict, tester=excluded.tester, notes=excluded.notes,"
        " created_at=datetime('now')",
        (ticket_id, device["schutzklasse"], device["heating_kw"],
         json.dumps(measurements, ensure_ascii=False), verdict, tester, notes),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM equipment_tests WHERE ticket_id = ?", (ticket_id,)
    ).fetchone()
    return _row_to_dict(row), 201