"""UI-Tests: Einseiten-App wird ausgeliefert (Task 10)."""
import flask


def test_root_serves_index(app_client):
    resp = app_client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "app.js" in html
    assert "style.css" in html


def test_static_app_js(app_client):
    resp = app_client.get("/static/app.js")
    assert resp.status_code == 200
    assert "Repair-Café" in resp.get_data(as_text=True)


def test_static_style_css(app_client):
    resp = app_client.get("/static/style.css")
    assert resp.status_code == 200


def test_static_print_css(app_client):
    resp = app_client.get("/static/print.css")
    assert resp.status_code == 200


def test_unknown_ticket_hash_route_still_serves_index(app_client):
    """Hash-Routing ist clientseitig: '/' liefert immer die SPA."""
    resp = app_client.get("/")
    assert resp.status_code == 200