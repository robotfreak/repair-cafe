"""Tests für den Assistenten-Endpoint (Task 9)."""
import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from app.assistant import OLLAMA_URL, SYSTEM_PROMPT, ask_ollama

WAIVER = {
    "signed_name": "Max Mustermann",
    "accepted": True,
    "signature_data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
}


def create_device(client, name):
    resp = client.post("/api/devices", json={"name": name})
    assert resp.status_code == 201
    return resp.get_json()["id"]


def create_ticket(client, device_id, fault):
    resp = client.post(
        "/api/tickets",
        json={"device_id": device_id, "fault_description": fault, "waiver": WAIVER},
    )
    assert resp.status_code == 201
    return resp.get_json()


@pytest.fixture
def ticket_id(app_client):
    device = create_device(app_client, "Netzteil Voltcraft")
    ticket = create_ticket(app_client, device, "Netzteil tot")
    return ticket["id"]


# ---------- SYSTEM_PROMPT / ask_ollama ----------

def test_system_prompt_key_aspects():
    """Der Prompt muss das Gem-Profil abbilden: sicherheitsfirst, phasenbasiert,
    interaktiv — und das Tagebuch als Faktenbasis (Regression: generische
    Antworten, die Erledigtes wiederholt haben)."""
    # Rolle & Philosophie
    assert "Repair-Café" in SYSTEM_PROMPT
    assert "Right to Repair" in SYSTEM_PROMPT
    # Sicherheit hat Priorität 1
    assert "Netzstecker" in SYSTEM_PROMPT
    assert "Kondensatoren" in SYSTEM_PROMPT
    # Phasen des Arbeitsablaufs
    assert "DIAGNOSE" in SYSTEM_PROMPT
    assert "ÖFFNEN" in SYSTEM_PROMPT
    assert "REPARATUR" in SYSTEM_PROMPT
    assert "ZUSAMMENBAU" in SYSTEM_PROMPT
    # Tagebuch-Anker (Regression)
    assert "Tagebuch" in SYSTEM_PROMPT
    assert "SCHON ERLEDIGT" in SYSTEM_PROMPT
    assert "OFFENE BEFUNDE" in SYSTEM_PROMPT
    assert "WAHRSCHEINLICHE URSACHEN" in SYSTEM_PROMPT
    # Erledigtes nicht erneut vorschlagen
    assert "NICHT erneut" in SYSTEM_PROMPT
    # Keine Erfindungen
    assert "Keine Erfindungen" in SYSTEM_PROMPT
    # Interaktivität: nächster Schritt + Rückfrage
    assert "Rückfrage" in SYSTEM_PROMPT
    assert "nächsten Schritt" in SYSTEM_PROMPT


def test_ask_ollama_sends_correct_payload():
    fake_resp = MagicMock()
    fake_resp.__enter__.return_value.read.return_value = json.dumps(
        {"message": {"content": "Erst messen, dann löten."}}
    ).encode("utf-8")
    with patch("app.assistant.urllib.request.urlopen", return_value=fake_resp) as mock_open:
        result = ask_ollama([{"role": "user", "content": "Netzteil tot"}])

    assert result == "Erst messen, dann löten."
    req = mock_open.call_args[0][0]
    assert req.get_method() == "POST"
    assert req.full_url == OLLAMA_URL
    assert mock_open.call_args.kwargs["timeout"] == 120
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["model"] == "phi4-mini"
    assert payload["stream"] is False
    assert payload["options"] == {"temperature": 0.3, "num_ctx": 8192, "num_predict": 400}
    assert payload["messages"] == [{"role": "user", "content": "Netzteil tot"}]


def test_ask_ollama_url_error():
    with patch(
        "app.assistant.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        with pytest.raises(RuntimeError) as excinfo:
            ask_ollama([{"role": "user", "content": "x"}])
    assert str(excinfo.value) == "Assistent-Backend nicht erreichbar"


def test_ask_ollama_timeout_error():
    with patch(
        "app.assistant.urllib.request.urlopen", side_effect=TimeoutError("timed out")
    ):
        with pytest.raises(RuntimeError) as excinfo:
            ask_ollama([{"role": "user", "content": "x"}])
    assert str(excinfo.value) == "Assistent-Backend nicht erreichbar"


def test_ask_ollama_http_error_with_body():
    err = urllib.error.HTTPError(
        OLLAMA_URL, 500, "Internal Server Error", None, io.BytesIO(b"model not found")
    )
    with patch("app.assistant.urllib.request.urlopen", side_effect=err):
        with pytest.raises(RuntimeError) as excinfo:
            ask_ollama([{"role": "user", "content": "x"}])
    assert "model not found" in str(excinfo.value)


def test_ask_ollama_error_key():
    fake_resp = MagicMock()
    fake_resp.__enter__.return_value.read.return_value = json.dumps(
        {"error": "Modell nicht geladen"}
    ).encode("utf-8")
    with patch("app.assistant.urllib.request.urlopen", return_value=fake_resp):
        with pytest.raises(RuntimeError) as excinfo:
            ask_ollama([{"role": "user", "content": "x"}])
    assert "Modell nicht geladen" in str(excinfo.value)


# ---------- Route POST /api/assistant/chat ----------

def test_chat_success(app_client, ticket_id):
    with patch("app.assistant.ask_ollama") as mock_ask:
        mock_ask.return_value = "Prüfe zuerst die Sicherung."
        resp = app_client.post(
            "/api/assistant/chat",
            json={"ticket_id": ticket_id, "question": "Wo fange ich an?"},
        )

    assert resp.status_code == 200
    assert resp.get_json() == {"answer": "Prüfe zuerst die Sicherung."}
    mock_ask.assert_called_once()
    messages = mock_ask.call_args[0][0]
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1]["role"] == "user"
    # user-Content enthält fault_description und die Frage
    assert "URSPRÜNGLICHER FEHLER (bei Annahme): Netzteil tot" in messages[1]["content"]
    assert "FRAGE DES NUTZERS: Wo fange ich an?" in messages[1]["content"]


def test_chat_empty_question_400(app_client, ticket_id):
    resp = app_client.post(
        "/api/assistant/chat", json={"ticket_id": ticket_id, "question": "   "}
    )
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Frage ist erforderlich"}


def test_chat_missing_ticket_id_400(app_client):
    resp = app_client.post("/api/assistant/chat", json={"question": "Was ist los?"})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "ticket_id ist erforderlich"}


def test_chat_invalid_ticket_id_400(app_client):
    resp = app_client.post(
        "/api/assistant/chat", json={"ticket_id": "abc", "question": "Was ist los?"}
    )
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "ticket_id ist erforderlich"}


def test_chat_unknown_ticket_404(app_client):
    with patch("app.assistant.ask_ollama") as mock_ask:
        resp = app_client.post(
            "/api/assistant/chat", json={"ticket_id": 9999, "question": "Was ist los?"}
        )
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Laufzettel nicht gefunden"}
    mock_ask.assert_not_called()


def test_chat_history_sent_to_backend(app_client, ticket_id):
    """Chat-Verlauf wird als messages mitgeschickt: context+Frage als user,
    bisherige Antworten als assistant — Grundlage für Rückfragen."""
    with patch("app.assistant.ask_ollama") as mock_ask:
        mock_ask.return_value = "Messpunkte A und B durchmessen."
        resp = app_client.post(
            "/api/assistant/chat",
            json={
                "ticket_id": ticket_id,
                "question": "Und wo genau messen?",
                "history": [
                    {"role": "assistant", "content": "Zuerst Primärseite prüfen."},
                    {"role": "user", "content": "Okay, Primärseite ist okay."},
                ],
            },
        )
    assert resp.status_code == 200
    messages = mock_ask.call_args[0][0]
    # system → context(user) → assistant → user → Frage
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[2] == {"role": "assistant", "content": "Zuerst Primärseite prüfen."}
    assert messages[3] == {"role": "user", "content": "Okay, Primärseite ist okay."}
    assert messages[4]["role"] == "user"
    assert "FRAGE DES NUTZERS: Und wo genau messen?" in messages[4]["content"]


def test_chat_history_empty_or_invalid_tolerant(app_client, ticket_id):
    """Fehlender/ungültiger Verlauf darf nie brechen (Alte-Clients-Kompatibilität)."""
    with patch("app.assistant.ask_ollama") as mock_ask:
        mock_ask.return_value = "ok"
        for bad in [None, [], "x", [42], [{"role": "user"}], [{"role": "nope", "content": "x"}]]:
            resp = app_client.post(
                "/api/assistant/chat",
                json={"ticket_id": ticket_id, "question": "Was tun?", "history": bad},
            )
            assert resp.status_code == 200, f"history={bad!r}"
            messages = mock_ask.call_args[0][0]
            # Nur gültige Einträge dürfen übrig bleiben
            for msg in messages[1:]:
                assert msg["role"] in {"user", "assistant"}
                assert isinstance(msg["content"], str) and msg["content"].strip()


def test_chat_history_size_capped(app_client, ticket_id):
    """Der Verlauf darf den Kontext nicht sprengen: letzte N Einträge, Rest verworfen."""
    with patch("app.assistant.ask_ollama") as mock_ask:
        mock_ask.return_value = "ok"
        big_history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Nachricht {i}"}
            for i in range(60)
        ]
        resp = app_client.post(
            "/api/assistant/chat",
            json={"ticket_id": ticket_id, "question": "Weiter?", "history": big_history},
        )
    assert resp.status_code == 200
    messages = mock_ask.call_args[0][0]
    history_msgs = messages[2:-1]  # ohne system + Kontext-Nachricht und ohne Frage-Msg
    assert len(history_msgs) <= 20


def test_chat_backend_error_503(app_client, ticket_id):
    with patch(
        "app.assistant.ask_ollama",
        side_effect=RuntimeError("Assistent-Backend nicht erreichbar"),
    ):
        resp = app_client.post(
            "/api/assistant/chat", json={"ticket_id": ticket_id, "question": "Was tun?"}
        )
    assert resp.status_code == 503
    assert resp.get_json() == {"error": "Assistent-Backend nicht erreichbar"}