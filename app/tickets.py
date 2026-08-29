import flask

from app.db import get_request_db
from app.waiver_text import WAIVER_VERSION
from app.waivers import save_signature, validate_waiver

bp = flask.Blueprint("tickets", __name__, url_prefix="/api/tickets")
# Separater Blueprint ohne url_prefix für das Board (liegt außerhalb von /api/tickets).
board_bp = flask.Blueprint("tickets_board", __name__)

TRANSITIONS = {
    "offen": {"in_arbeit"},
    "in_arbeit": {"erfolgreich", "nicht_reparierbar", "offen"},
    "erfolgreich": {"abgeholt"},
    "nicht_reparierbar": {"abgeholt"},
    "abgeholt": set(),
}

TIMESTAMP_FIELD = {
    "in_arbeit": "started_at",
    "erfolgreich": "finished_at",
    "nicht_reparierbar": "finished_at",
    "abgeholt": "picked_up_at",
}

VALID_STATUSES = ("offen", "in_arbeit", "erfolgreich", "nicht_reparierbar", "abgeholt")

FAULT_MAX = 2000
ASSIGNEE_MAX = 100


def can_transition(old, new):
    """True genau dann, wenn der Übergang old → new laut Statusmaschine erlaubt ist."""
    return new in TRANSITIONS.get(old, set())


def _fetch_ticket(conn, ticket_id):
    return conn.execute(
        "SELECT t.*, d.name AS device_name, d.schutzklasse, d.heating_kw"
        " FROM tickets t"
        " JOIN devices d ON d.id = t.device_id"
        " WHERE t.id = ?",
        (ticket_id,),
    ).fetchone()


@bp.route("", methods=["POST"])
def create_ticket():
    payload = flask.request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}

    conn = get_request_db(flask.current_app)

    # 1) Gerät muss existieren
    device_id = payload.get("device_id")
    if not isinstance(device_id, int) or isinstance(device_id, bool):
        return {"error": "Gerät nicht gefunden"}, 404
    if conn.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone() is None:
        return {"error": "Gerät nicht gefunden"}, 404

    # 2) Fehlerbeschreibung
    fault = payload.get("fault_description")
    if not isinstance(fault, str) or not fault.strip():
        return {"error": "Fehlerbeschreibung ist erforderlich"}, 400
    fault = fault.strip()
    if len(fault) > FAULT_MAX:
        return {"error": "Fehlerbeschreibung darf höchstens 2000 Zeichen lang sein"}, 400

    # 3) Pflicht-Waiver
    ok, msg, cleaned = validate_waiver(payload.get("waiver"))
    if not ok:
        return {"error": msg}, 400

    assignee = payload.get("assignee")
    if assignee is not None:
        if not isinstance(assignee, str):
            return {"error": "assignee muss ein Textfeld sein"}, 400
        assignee = assignee.strip()
        if len(assignee) > ASSIGNEE_MAX:
            return {"error": "assignee darf höchstens 100 Zeichen lang sein"}, 400

    # Transaktion: Ticket, Signaturdatei, Waiver-Zeile
    cur = conn.execute(
        "INSERT INTO tickets (device_id, fault_description, assignee) VALUES (?, ?, ?)",
        (device_id, fault, assignee),
    )
    ticket_id = cur.lastrowid
    try:
        sig_path = save_signature(
            flask.current_app.config["DATA_DIR"], ticket_id, cleaned["signature_data_url"]
        )
    except ValueError as exc:
        conn.rollback()
        return {"error": str(exc)}, 400

    conn.execute(
        "INSERT INTO waivers (ticket_id, waiver_version, signed_name, accepted, signature_path)"
        " VALUES (?, ?, ?, 1, ?)",
        (ticket_id, WAIVER_VERSION, cleaned["signed_name"], sig_path),
    )
    conn.commit()

    row = _fetch_ticket(conn, ticket_id)
    return dict(row), 201


@bp.route("", methods=["GET"])
def list_tickets():
    conn = get_request_db(flask.current_app)
    status = flask.request.args.get("status", "").strip()
    if status:
        if status not in VALID_STATUSES:
            return {
                "error": "Ungültiger Status. Erlaubt sind: " + ", ".join(VALID_STATUSES)
            }, 400
        rows = conn.execute(
            "SELECT t.*, d.name AS device_name, d.schutzklasse FROM tickets t"
            " JOIN devices d ON d.id = t.device_id"
            " WHERE t.status = ?"
            " ORDER BY t.created_at DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT t.*, d.name AS device_name, d.schutzklasse FROM tickets t"
            " JOIN devices d ON d.id = t.device_id"
            " ORDER BY t.created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@bp.route("/<int:ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    conn = get_request_db(flask.current_app)
    row = _fetch_ticket(conn, ticket_id)
    if row is None:
        return {"error": "Laufzettel nicht gefunden"}, 404
    return dict(row)


@bp.route("/<int:ticket_id>/status", methods=["POST"])
def change_status(ticket_id):
    payload = flask.request.get_json(silent=True)
    new_status = payload.get("status") if isinstance(payload, dict) else None

    conn = get_request_db(flask.current_app)
    row = _fetch_ticket(conn, ticket_id)
    if row is None:
        return {"error": "Laufzettel nicht gefunden"}, 404

    old_status = row["status"]
    if not isinstance(new_status, str) or not can_transition(old_status, new_status):
        return {
            "error": f"Übergang von '{old_status}' nach '{new_status}' ist nicht erlaubt"
        }, 400

    sets = ["status = ?"]
    params = [new_status]
    field = TIMESTAMP_FIELD.get(new_status)
    if field:
        sets.append(f"{field} = datetime('now')")
    params.append(ticket_id)
    conn.execute(f"UPDATE tickets SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()

    updated = _fetch_ticket(conn, ticket_id)
    return dict(updated)


@board_bp.route("/api/board", methods=["GET"])
def board():
    conn = get_request_db(flask.current_app)
    rows = conn.execute(
        "SELECT t.*, d.name AS device_name, d.schutzklasse FROM tickets t"
        " JOIN devices d ON d.id = t.device_id"
        " ORDER BY t.created_at DESC"
    ).fetchall()
    board = {status: [] for status in VALID_STATUSES}
    for row in rows:
        ticket = dict(row)
        if ticket["status"] in board:
            board[ticket["status"]].append(ticket)
    return board