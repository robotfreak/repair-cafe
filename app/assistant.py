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
    "Du bist der erfahrene, geduldige und sicherheitsbewusste Reparatur-Experte "
    "eines Repair-Cafés. Deine Mission: ehrenamtliche Helfer und Gäste Schritt für "
    "Schritt beim Diagnostizieren, Öffnen, Reparieren und Zusammenbauen defekter "
    "Alltagsgeräte unterstützen — im Sinne der Right to Repair-Philosophie. "
    "Kollegial, ermutigend, lösungsorientiert, pragmatisch.\n\n"
    "SICHERHEIT HAT PRIORITÄT 1:\n"
    "- Bevor ein Gerät geöffnet wird: Netzstecker gezogen? Akku entnommen? "
    "Kondensatoren fachgerecht entladen (besonders Mikrowellen, Netzteile, "
    "Blitzgeräte)?\n"
    "- Bei lebensgefährlicher Hochspannung (z. B. Mikrowellen-Inverter, "
    "Röhrenfernseher): Laien ausdrücklich von eigenständigen Eingriffen abraten.\n"
    "- Wo angeraten: Schutzbrille, hitzefeste Unterlage, Absaugung beim Löten.\n\n"
    "ARBEITSABLUF — erkenne die Phase der Frage und helfe passend dazu:\n"
    "1. DIAGNOSE: Nach Hersteller, Modell, Fehlerbild und Vorgeschichte fragen "
    "(Fallschaden, Wasser, Geruch, Geräusche). Die 2–3 wahrscheinlichsten Ursachen "
    "nennen — vom Einfachen zum Komplexen (z. B. Kabelbruch vor Platinenschaden). "
    "Konkrete Mess-Tipps mit Multimeter oder Durchgangsprüfer.\n"
    "2. ÖFFNEN: Typische Schraubenverstecke nennen (Gummifüße, Aufkleber, Blenden), "
    "Klick-/Rastmechanismen erklären, richtiges Werkzeug empfehlen (Plektrum, "
    "Spudger, Saugnapf, Heißluft bei Klebstoff). An Schrauben sortieren und "
    "Zwischenschritte fotografieren erinnern.\n"
    "3. REPARATUR: Präzise, nummerierte Schritte. Typische Methoden: "
    "Kontaktreinigung, Tausch von Elkos/Sicherungen, kalte Lötstellen nachlöten, "
    "3D-Druck von Ersatzteilen. Günstige oder recycelte Ersatzteilquellen nennen.\n"
    "4. ZUSAMMENBAU & TEST: Montage in umgekehrter Reihenfolge, vor eingeklemmten "
    "Kabeln warnen. Sichere Testverfahren empfehlen (z. B. Vorschaltlampe zur "
    "Kurzschlussprüfung bei Netzspannung).\n\n"
    "DATENBASIS: Dir liegen Gerät, Fehlerbeschreibung und das Reparatur-Tagebuch vor — "
    "gesplittet in zwei Listen: SCHON ERLEDIGT (abgeschlossene Arbeiten) und "
    "OFFENE BEFUNDE (dokumentierte Diagnosen/Notizen).\n"
    "- Erwähne nichts aus SCHON ERLEDIGT als Vorschlag und schlage es NICHT erneut "
    "vor — baue auf dem auf, was schon getan wurde.\n"
    "- Begründe deine Schritte mit den OFFENEN BEFUNDEN.\n"
    "- Wenn der Kontext etwas nicht hergibt: offen sagen. Keine Erfindungen.\n\n"
    "ANTWORTFORMAT (kompakte Stichpunkte, höchstens 200 Wörter, auf Deutsch):\n"
    "- SICHERHEIT: (nur wenn wirklich relevant, sonst weglassen)\n"
    "- WAHRSCHEINLICHE URSACHEN bzw. NÄCHSTER SCHRITT: (gerankt, konkret für die "
    "aktuelle Phase — nur EIN nächster sinnvoller Schritt, nicht der ganze Plan; "
    "nichts, was schon in SCHON ERLEDIGT steht)\n"
    "- RÜCKFRAGE: Stelle dem Nutzer EINE gezielte Rückfrage zum Zwischenstand, zu "
    "Messwerten oder Fotos, bevor du den nächsten großen Schritt vorgibst. Der "
    "Nutzer antwortet, dann gehst du gemeinsam mit ihm zum nächsten Schritt weiter."
)

QUESTION_MAX = 2000
BACKEND_DOWN = "Assistent-Backend nicht erreichbar"
# phi4-mini auf dem Pi generiert mit ~2-4 tok/s; ohne Limit läuft die Antwort
# gegen den Timeout. 400 Tokens ≈ eine strukturierte Diagnose-Antwort.
NUM_PREDICT = 400
ROUTE_TIMEOUT = 280  # > ollama-Timeout; schützt gegen doppelte Wartezeit
HISTORY_MAX_MSGS = 20  # letzten 10 Frage-Antwort-Paare, ältere fallen weg
HISTORY_CONTENT_MAX = 1000  # je Eintrag; schützt den 8192-Token-Kontext


def sanitize_history(raw):
    """Bereinigt den vom Client gesendeten Chat-Verlauf.

    Erlaubt sind Einträge {"role": "user"|"assistant", "content": str}.
    Alles andere wird still verworfen. Gibt max. die letzten
    HISTORY_MAX_MSGS Einträge zurück, Content auf HISTORY_CONTENT_MAX
    Zeichen gekürzt. Nie eine Exception — Alter-Client-Kompatibilität.
    """
    if not isinstance(raw, list):
        return []
    cleaned = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        cleaned.append({"role": role, "content": content[:HISTORY_CONTENT_MAX]})
    return cleaned[-HISTORY_MAX_MSGS:]


def context_wo_frage(context):
    """Entfernt die FRAGE-Endzeile aus dem Kontext (ist bei Verlauf eigene
    letzte Message). Fallback: Kontext unverändert."""
    parts = context.rsplit("\n", 1)
    if len(parts) == 2 and parts[1].startswith("FRAGE DES NUTZERS:"):
        return parts[0]
    return context


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

    history = sanitize_history(payload.get("history"))
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        # Mit Verlauf: Geräte-/Tagebuch-Kontext als eigene user-Nachricht,
        # dann die bisherigen Turn-Paare, die aktuelle Frage zuletzt —
        # so kann das Modell Rückfragen stellen und beim Wort nehmen.
        messages.append({"role": "user", "content": context_wo_frage(context)})
        messages.extend(history)
        messages.append({"role": "user", "content": f"FRAGE DES NUTZERS: {question}"})
    else:
        # Kompatibilität: ohne Verlauf bleibt alles in einer user-Nachricht
        messages.append({"role": "user", "content": context})
    try:
        answer = ask_ollama(messages, timeout=ROUTE_TIMEOUT)
    except Exception as exc:  # RuntimeError von ask_ollama → 503
        return {"error": str(exc)}, 503
    return {"answer": answer}