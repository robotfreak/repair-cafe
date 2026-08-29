"""Tests: Tagebuch-Korrekturen (PATCH/DELETE), Duplikatschutz, Dokument-DELETE."""
import io

PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
       "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def make_ticket(app_client, name="Tagebuch-Test"):
    did = app_client.post("/api/devices", json={"name": name}).get_json()["id"]
    return app_client.post(
        "/api/tickets",
        json={"device_id": did, "fault_description": "kaputt",
              "waiver": {"signed_name": "M M", "accepted": True,
                         "signature_data_url": PNG}}).get_json()["id"]


def make_entry(app_client, tid, content="Erster Eintrag", entry_type="notiz", author=None):
    resp = app_client.post(
        f"/api/tickets/{tid}/entries",
        json={"content": content, "entry_type": entry_type, "author": author})
    assert resp.status_code == 201
    return resp.get_json()


# ---------- Journal PATCH ----------

def test_patch_content_setzt_edit_marker(app_client):
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "ELKO geplatx", author="Anna")
    resp = app_client.patch(
        f"/api/tickets/{tid}/entries/{entry['id']}",
        json={"content": "ELKO am Netzteil geplatzt (220uF/100V)", "author": "Peter"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["content"].startswith("ELKO am Netzteil")
    assert data["edited_at"] is not None
    assert data["edited_by"] == "Peter"
    assert data["author"] == "Anna"  # Original-Autor unverändert


def test_patch_original_author_bleibt(app_client):
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "Original von Anna", author="Anna")
    data = app_client.patch(
        f"/api/tickets/{tid}/entries/{entry['id']}",
        json={"content": "Korrigiert von Peter", "author": "Peter"}).get_json()
    assert data["author"] == "Anna"          # Ersteller bleibt
    assert data["edited_by"] == "Peter"      # Bearbeiter steht separat


def test_patch_entry_typ(app_client):
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "Diagnose korrigiert")
    resp = app_client.patch(
        f"/api/tickets/{tid}/entries/{entry['id']}", json={"entry_type": "diagnose"})
    assert resp.get_json()["entry_type"] == "diagnose"


def test_patch_leerer_inhalt_400(app_client):
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "Text")
    for bad in ("", "   "):
        resp = app_client.patch(
            f"/api/tickets/{tid}/entries/{entry['id']}",
            json={"content": bad})
        assert resp.status_code == 400


def test_patch_fuellt_leeren_autor_nach(app_client):
    """Einträge ohne Autor („unbekannt") bekommen beim ersten Bearbeiten den Namen."""
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "Ohne Autor angelegt", author=None)
    assert entry["author"] is None
    data = app_client.patch(
        f"/api/tickets/{tid}/entries/{entry['id']}",
        json={"content": entry["content"], "author": "Peter"}).get_json()
    assert data["author"] == "Peter"    # nachgefüllt als Original-Autor
    assert data["edited_by"] == "Peter"


def test_patch_ueberschreibt_kein_vorhandenes_autorfeld(app_client):
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "Anns Eintrag", author="Anna")
    data = app_client.patch(
        f"/api/tickets/{tid}/entries/{entry['id']}",
        json={"content": "Korrigiert", "author": "Peter"}).get_json()
    assert data["author"] == "Anna"     # bleibt
    assert data["edited_by"] == "Peter"


def test_patch_ohne_author_laesst_alles_unveraendert(app_client):
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "Ohne Autor", author=None)
    data = app_client.patch(
        f"/api/tickets/{tid}/entries/{entry['id']}",
        json={"content": "Korrigiert ohne Namensangabe"}).get_json()
    assert data["author"] is None  # kein Name übermittelt → bleibt unbekannt


def test_patch_zu_lang_400(app_client):
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "x")
    resp = app_client.patch(
        f"/api/tickets/{tid}/entries/{entry['id']}",
        json={"content": "y" * 5001})
    assert resp.status_code == 400


def test_patch_404_fremdes_ticket(app_client):
    tid = make_ticket(app_client, "Ticket-A")
    other = make_ticket(app_client, "Ticket-B")
    entry = make_entry(app_client, other)
    resp = app_client.patch(
        f"/api/tickets/{tid}/entries/{entry['id']}", json={"content": "hijack"})
    assert resp.status_code == 404


def test_patch_leerer_payload_400(app_client):
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "Text")
    resp = app_client.patch(f"/api/tickets/{tid}/entries/{entry['id']}", json={})
    assert resp.status_code == 400


# ---------- Journal DELETE ----------

def test_delete_entry(app_client):
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "Wird gelöscht")
    resp = app_client.delete(f"/api/tickets/{tid}/entries/{entry['id']}")
    assert resp.status_code == 200
    entries = app_client.get(f"/api/tickets/{tid}/entries").get_json()
    assert all(e["id"] != entry["id"] for e in entries)


def test_delete_entry_404(app_client):
    tid = make_ticket(app_client)
    assert app_client.delete(f"/api/tickets/{tid}/entries/999").status_code == 404


# ---------- FTS-Konsistenz nach UPDATE/DELETE ----------

def test_fts_aktualisiert_sich_bei_patch_und_delete(app_client):
    tid = make_ticket(app_client)
    entry = make_entry(app_client, tid, "Kondensator im Netzteil geplatzt")
    eid = entry["id"]

    hit_before = app_client.get("/api/search?q=Kondensator").get_json()
    assert any(h["id"] == eid for h in hit_before["journal"])

    # Korrektur: Text ändert sich → alter Begriff muss verschwinden, neuer gefunden werden
    app_client.patch(f"/api/tickets/{tid}/entries/{eid}", json={"content": "Elko geplatzt"})
    hit_after = app_client.get("/api/search?q=kondensator").get_json()
    assert not any(h["id"] == eid for h in hit_after["journal"])
    hit_new = app_client.get("/api/search?q=elko").get_json()
    assert any(h["id"] == eid for h in hit_new["journal"])

    # Löschen → Treffer weg
    app_client.delete(f"/api/tickets/{tid}/entries/{eid}")
    hit_deleted = app_client.get("/api/search?q=elko").get_json()
    assert not any(h["id"] == eid for h in hit_deleted["journal"])


# ---------- Duplikatschutz + Dokument-DELETE ----------

def test_duplikat_upload_409(app_client):
    tid = make_ticket(app_client, "Duplikat-Gerät")
    data = b"%PDF-1.4 test-content-" + b"x" * 100
    first = app_client.post(
        "/api/documents",
        data={"file": (io.BytesIO(data), "handbuch.pdf"),
              "title": "HM-Handbuch", "doc_type": "manual", "ticket_id": str(tid)},
        content_type="multipart/form-data")
    assert first.status_code == 201
    second = app_client.post(
        "/api/documents",
        data={"file": (io.BytesIO(data), "handbuch.pdf"),
              "title": "HM-Handbuch (2)", "doc_type": "manual", "ticket_id": str(tid)},
        content_type="multipart/form-data")
    assert second.status_code == 409
    assert "bereits" in second.get_json()["error"]


def test_duplikat_andere_ticket_erlaubt(app_client):
    """Dieselbe Datei an einem ANDEREN Ticket ist erlaubt (seltener Sonderfall)."""
    tid1 = make_ticket(app_client, "Gerät 1")
    tid2 = make_ticket(app_client, "Gerät 2")
    data = b"%PDF-1.4 content-" + b"z" * 50
    r1 = app_client.post("/api/documents",
                     data={"file": (io.BytesIO(data), "a.pdf"), "title": "A",
                           "doc_type": "manual", "ticket_id": str(tid1)},
                     content_type="multipart/form-data")
    r2 = app_client.post("/api/documents",
                     data={"file": (io.BytesIO(data), "b.pdf"), "title": "B",
                           "doc_type": "manual", "ticket_id": str(tid2)},
                     content_type="multipart/form-data")
    assert r1.status_code == 201 and r2.status_code == 201


def test_delete_dokument_entfernt_zeile_und_datei(app_client, tmp_path):
    tid = make_ticket(app_client, "Lösch-Gerät")
    data = b"%PDF-1.4 to-be-deleted " + b"q" * 60
    created = app_client.post(
        "/api/documents",
        data={"file": (io.BytesIO(data), "loesch.pdf"), "title": "Weg damit",
              "doc_type": "manual", "ticket_id": str(tid)},
        content_type="multipart/form-data")
    assert created.status_code == 201, created.get_data(as_text=True)
    doc_id = created.get_json()["id"]

    resp = app_client.delete(f"/api/documents/{doc_id}")
    assert resp.status_code == 200
    assert app_client.get(f"/api/documents/{doc_id}").status_code == 404
    assert app_client.get(f"/api/documents/{doc_id}/file").status_code == 404


def test_delete_dokument_404(app_client):
    assert app_client.delete("/api/documents/999").status_code == 404