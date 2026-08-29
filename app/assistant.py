"""Ollama-Assistent: SYSTEM_PROMPT, ask_ollama und POST /api/assistant/chat (Task 9)."""
import json
import urllib.error
import urllib.request

import flask

from app.context_builder import build_context
from app.db import get_request_db

bp = flask.Blueprint("assistant", __name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "phi4-mini"

SYSTEM_PROMPT = (
    "Du bist ein erfahrener Elektronik-Reparateur in einem Repair-Café.\n\n"
    "Dir liegen Gerät, Fehlerbeschreibung und das Reparatur-Tagebuch vor. GEHE SO VOR:\n\n"
    "1. Lies das Tagebuch aufmerksam: Was wurde zuletzt geändert/getauscht/repariert? "
    "Welche Symptome sind dokumentiert?\n"
    "2. Verbinde die Fakten: Deine Antwort muss sich auf diese Fakten stützen "
    "(Zeitpunkt des Auftretens, Zusammenhang mit letzten Arbeiten, typische Bauteil-Ausfälle).\n"
    "3. Trenne klar: FAKTEN AUS DEM TAGEBUCH vs. VERMUTUNGEN. Nenne typische "
    "elektronische Ursachen für das beschriebene Symptom (z. B. wandernde Nulllinie "
    "nach Einschalten: Temperaturdrift von Bauteilen, alternde Elkos, Kalibrierung).\n"
    "4. Wiederhole NICHT bereits erledigte Arbeitsschritte als Vorschläge. "
    "Baue auf dem auf, was schon getan wurde.\n"
    "5. Wenn der Kontext die Antwort nicht hergibt, sage das offen. Keine Erfindungen.\n\n"
    "ANTWORTFORMAT (kompakt, Stichpunkte, höchstens 250 Wörter, auf Deutsch):\n"
    "- FAKTEN AUS DEM TAGEBUCH: (was für die Frage relevant ist)\n"
    "- WAHRSCHEINLICHE URSACHEN: (gerankt, mit Begründung aus dem Tagebuch)\n"
    "- PRÜFSCHRITTE: (konkret, mit Multimeter/Oszilloskop)\n"
    "- SICHERHEIT: (nur wenn wirklich relevant, sonst weglassen)"
)

QUESTION_MAX = 2000
BACKEND_DOWN = "Assistent-Backend nicht erreichbar"
# phi4-mini auf dem Pi generiert mit ~2-4 tok/s; ohne Limit läuft die Antwort
# gegen den Timeout. 400 Tokens ≈ eine strukturierte Diagnose-Antwort.
NUM_PREDICT = 400
ROUTE_TIMEOUT = 280  # > ollama-Timeout; schützt gegen doppelte Wartezeit


def ask_ollama(messages, timeout=120):
    """Sendet messages an Ollama und liefert message.content zurück.

    Wirft RuntimeError mit deutscher Meldung bei Netz-/HTTP-/Antwortfehlern.
    """
    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.3, "num_ctx": 8192, "num_predict": NUM_PREDICT},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except (urllib.error.HTTPError) as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except OSError:
            detail = ""
        raise RuntimeError(f"Assistent-Backend-Fehler: {detail or exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(BACKEND_DOWN) from exc

    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("Assistent-Backend lieferte keine gültige Antwort") from exc

    if "error" in data:
        raise RuntimeError(str(data["error"]))
    try:
        return data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("Assistent-Backend lieferte keine Antwort") from exc


@bp.route("/api/assistant/chat", methods=["POST"])
def chat():
    payload = flask.request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}

    ticket_id = payload.get("ticket_id")
    if not isinstance(ticket_id, int) or isinstance(ticket_id, bool):
        return {"error": "ticket_id ist erforderlich"}, 400

    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        return {"error": "Frage ist erforderlich"}, 400
    question = question.strip()
    if len(question) > QUESTION_MAX:
        return {"error": "Frage darf höchstens 2000 Zeichen lang sein"}, 400

    conn = get_request_db(flask.current_app)
    try:
        context = build_context(conn, ticket_id, question)
    except ValueError:
        return {"error": "Laufzettel nicht gefunden"}, 404

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context},
    ]
    try:
        answer = ask_ollama(messages, timeout=ROUTE_TIMEOUT)
    except Exception as exc:  # RuntimeError von ask_ollama → 503
        return {"error": str(exc)}, 503
    return {"answer": answer}