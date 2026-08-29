import base64
import binascii
import os
import uuid

import flask

from app.db import get_request_db
from app.waiver_text import WAIVER_TEXT, WAIVER_VERSION

bp = flask.Blueprint("waivers", __name__)

MAX_SIGNATURE_BYTES = 500_000
PNG_PREFIX = "data:image/png;base64,"
NAME_MAX = 100
MISSING_WAIVER_MSG = "Haftungsausschluss muss akzeptiert und unterschrieben werden"


def validate_waiver(waiver):
    """Prüft ein Waiver-Dict für die Ticket-Anlage.

    Rückgabe: (ok, fehlermeldung, aufgeräumtes_dict).
    """
    if not waiver or not isinstance(waiver, dict):
        return False, MISSING_WAIVER_MSG, None

    signed_name = waiver.get("signed_name")
    if not isinstance(signed_name, str) or not signed_name.strip():
        return False, "Name auf dem Haftungsausschluss ist erforderlich", None
    signed_name = signed_name.strip()
    if len(signed_name) > NAME_MAX:
        return False, "Name darf höchstens 100 Zeichen lang sein", None

    if waiver.get("accepted") is not True:
        return False, "Haftungsausschluss muss akzeptiert werden", None

    signature = waiver.get("signature_data_url")
    if not isinstance(signature, str) or not signature.startswith(PNG_PREFIX):
        return False, "Signatur muss als PNG-Daten-URL übergeben werden", None

    cleaned = {
        "signed_name": signed_name,
        "accepted": True,
        "signature_data_url": signature,
    }
    return True, None, cleaned


def save_signature(data_dir, ticket_id, data_url):
    """Dekodiert eine PNG-Daten-URL und speichert sie unter signatures/.

    Gibt den relativen Pfad 'signatures/<dateiname>' zurück.
    Wirft ValueError bei ungültiger Data-URL oder Überschreitung der Größe.
    """
    if not isinstance(data_url, str) or not data_url.startswith(PNG_PREFIX):
        raise ValueError("Ungültige Signatur-Daten-URL (nur image/png erlaubt)")

    b64_part = data_url[len(PNG_PREFIX):]
    try:
        raw = base64.b64decode(b64_part, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Ungültige Base64-Kodierung in der Signatur") from exc

    if len(raw) > MAX_SIGNATURE_BYTES:
        raise ValueError(
            f"Signatur ist zu groß (max. {MAX_SIGNATURE_BYTES} Bytes)"
        )

    sig_dir = os.path.join(data_dir, "signatures")
    os.makedirs(sig_dir, exist_ok=True)
    filename = f"waiver-{ticket_id}-{uuid.uuid4().hex[:8]}.png"
    with open(os.path.join(sig_dir, filename), "wb") as fh:
        fh.write(raw)
    return f"signatures/{filename}"


@bp.route("/api/waiver", methods=["GET"])
def get_waiver_text():
    return {"text": WAIVER_TEXT, "version": WAIVER_VERSION}


@bp.route("/api/waivers/<int:waiver_id>/signature", methods=["GET"])
def get_signature(waiver_id):
    conn = get_request_db(flask.current_app)
    row = conn.execute(
        "SELECT signature_path FROM waivers WHERE id = ?", (waiver_id,)
    ).fetchone()
    if row is None or not row["signature_path"]:
        return {"error": "Signatur nicht gefunden"}, 404

    data_dir = os.path.abspath(flask.current_app.config["DATA_DIR"])
    full_path = os.path.abspath(
        os.path.normpath(os.path.join(data_dir, row["signature_path"]))
    )
    if os.path.commonpath([data_dir, full_path]) != data_dir:
        return {"error": "Signatur nicht gefunden"}, 404
    if not os.path.isfile(full_path):
        return {"error": "Signatur nicht gefunden"}, 404

    return flask.send_file(full_path, mimetype="image/png")


@bp.route("/api/tickets/<int:ticket_id>/waiver", methods=["GET"])
def get_ticket_waiver(ticket_id):
    conn = get_request_db(flask.current_app)
    row = conn.execute(
        "SELECT id, signed_name, waiver_version, signed_at FROM waivers"
        " WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchone()
    if row is None:
        return {"error": "Kein Haftungsausschluss zum Laufzettel gefunden"}, 404

    return {
        "signed_name": row["signed_name"],
        "waiver_version": row["waiver_version"],
        "signed_at": row["signed_at"],
        "signature_url": f"/api/waivers/{row['id']}/signature",
    }