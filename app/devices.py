import flask

from app.db import get_request_db

bp = flask.Blueprint("devices", __name__, url_prefix="/api/devices")

TEXT_FIELDS = (
    "category",
    "manufacturer",
    "model",
    "serial_number",
    "owner_name",
    "owner_contact",
    "accessories",
)
SPECIAL_FIELDS = ("schutzklasse", "heating_kw")
ALL_FIELDS = ("name",) + TEXT_FIELDS + SPECIAL_FIELDS
NAME_MAX = 200
FIELD_MAX = 500


def _validate(payload, partial=False):
    """Gibt (fehlermeldung|None, aufgeräumte_felder) zurück."""
    data = {}
    if not isinstance(payload, dict):
        return "Name ist erforderlich", data

    keys = ALL_FIELDS if not partial else [k for k in ALL_FIELDS if k in payload]

    if not partial or "name" in payload:
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            return "Name ist erforderlich", data
        name = name.strip()
        if len(name) > NAME_MAX:
            return "Name darf höchstens 200 Zeichen lang sein", data
        data["name"] = name

    if "schutzklasse" in keys:
        value = payload.get("schutzklasse")
        if value is None:
            data["schutzklasse"] = None
        elif isinstance(value, str) and value.strip().upper() in ("I", "II", "III"):
            data["schutzklasse"] = value.strip().upper()
        else:
            return "schutzklasse muss I, II oder III sein", data

    if "heating_kw" in keys:
        value = payload.get("heating_kw")
        if value is None:
            data["heating_kw"] = None
        elif isinstance(value, bool) or not isinstance(value, (int, float)):
            return "heating_kw muss eine Zahl sein", data
        elif value <= 0:
            return "heating_kw muss größer 0 sein", data
        else:
            data["heating_kw"] = round(float(value), 2)

    for field in keys:
        if field == "name" or field in SPECIAL_FIELDS:
            continue
        if field not in payload or payload[field] is None:
            continue
        value = payload[field]
        if not isinstance(value, str):
            return f"{field} muss ein Textfeld sein", data
        value = value.strip()
        if len(value) > FIELD_MAX:
            return f"{field} darf höchstens 500 Zeichen lang sein", data
        data[field] = value

    return None, data


@bp.route("", methods=["POST"])
def create_device():
    error, data = _validate(flask.request.get_json(silent=True))
    if error:
        return {"error": error}, 400

    conn = get_request_db(flask.current_app)
    cols = ", ".join(data.keys())
    marks = ", ".join("?" for _ in data)
    cur = conn.execute(f"INSERT INTO devices ({cols}) VALUES ({marks})", tuple(data.values()))
    conn.commit()

    row = conn.execute("SELECT * FROM devices WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row), 201


@bp.route("", methods=["GET"])
def list_devices():
    q = flask.request.args.get("q", "").strip()
    conn = get_request_db(flask.current_app)
    if q:
        like = f"%{q.lower()}%"
        rows = conn.execute(
            "SELECT * FROM devices WHERE LOWER(name) LIKE ?"
            " OR LOWER(manufacturer) LIKE ? OR LOWER(model) LIKE ?"
            " ORDER BY name",
            (like, like, like),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM devices ORDER BY name").fetchall()
    return [dict(r) for r in rows]


@bp.route("/<int:device_id>", methods=["GET"])
def get_device(device_id):
    conn = get_request_db(flask.current_app)
    row = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    if row is None:
        return {"error": "Gerät nicht gefunden"}, 404
    return dict(row)


@bp.route("/<int:device_id>", methods=["PATCH"])
def update_device(device_id):
    payload = flask.request.get_json(silent=True)
    error, data = _validate(payload, partial=True)
    if error:
        return {"error": error}, 400
    if not data:
        return {"error": "Keine gültigen Felder zum Aktualisieren übergeben"}, 400

    conn = get_request_db(flask.current_app)
    row = conn.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone()
    if row is None:
        return {"error": "Gerät nicht gefunden"}, 404

    sets = ", ".join(f"{col} = ?" for col in data)
    conn.execute(
        f"UPDATE devices SET {sets} WHERE id = ?",
        tuple(data.values()) + (device_id,),
    )
    conn.commit()

    updated = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    return dict(updated)


@bp.route("/<int:device_id>", methods=["DELETE"])
def delete_device(device_id):
    conn = get_request_db(flask.current_app)
    row = conn.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone()
    if row is None:
        return {"error": "Gerät nicht gefunden"}, 404

    count = conn.execute(
        "SELECT COUNT(*) AS n FROM tickets WHERE device_id = ?", (device_id,)
    ).fetchone()["n"]
    if count:
        return {"error": "Gerät hat Laufzettel und kann nicht gelöscht werden"}, 409

    conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
    conn.commit()
    return {"ok": True}