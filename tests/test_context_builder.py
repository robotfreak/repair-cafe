"""Tests für den Kontext-Builder (Task 8)."""
import pytest

from app.context_builder import build_context, extract_keywords
from app.db import get_db

DEVICE = {
    "name": "Netzteil Voltcraft",
    "category": "Netzteil",
    "manufacturer": "Voltcraft",
    "model": "PS-123",
}
FAULT = "Netzteil tot"
QUESTION = "Was tun?"


def seed_ticket_with_journal(conn, fault=FAULT, entries=12):
    """Gerät + Ticket mit Journal-Einträgen; Eintrag 5 erwähnt 'Netzteil' (FTS-Filter-Test)."""
    cur = conn.execute(
        "INSERT INTO devices (name, category, manufacturer, model) VALUES (?, ?, ?, ?)",
        (DEVICE["name"], DEVICE["category"], DEVICE["manufacturer"], DEVICE["model"]),
    )
    device_id = cur.lastrowid
    cur = conn.execute(
        "INSERT INTO tickets (device_id, fault_description, status) VALUES (?, ?, 'in_arbeit')",
        (device_id, fault),
    )
    ticket_id = cur.lastrowid
    for i in range(1, entries + 1):
        content = (
            "Netzteil geöffnet, Lüfter dreht nicht"
            if i == 5
            else f"Schritt {i}: gemessen und dokumentiert"
        )
        conn.execute(
            "INSERT INTO journal_entries (ticket_id, author, entry_type, content, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                ticket_id,
                "Max" if i % 2 else None,
                "schritt" if i % 2 else "notiz",
                content,
                f"2026-08-01 10:{i:02d}:00",
            ),
        )
    conn.commit()
    return device_id, ticket_id


def seed_other_repair(conn):
    """Zweites Gerät + Ticket mit Eintrag, der den Begriff 'Netzteil' enthält."""
    cur = conn.execute("INSERT INTO devices (name) VALUES ('Verstärker Marantz')")
    device_id = cur.lastrowid
    cur = conn.execute(
        "INSERT INTO tickets (device_id, fault_description) VALUES (?, 'Kein Ton')",
        (device_id,),
    )
    ticket_id = cur.lastrowid
    conn.execute(
        "INSERT INTO journal_entries (ticket_id, author, entry_type, content, created_at)"
        " VALUES (?, 'Anna', 'diagnose', ?, '2026-07-20 09:00:00')",
        (ticket_id, "Kondensator im Netzteil Elko aufgequollen, getauscht"),
    )
    conn.commit()
    return ticket_id


# ---------- Heuristik extract_keywords ----------

def test_extract_keywords_filters_and_dedupes():
    assert extract_keywords("Der Kondensator ELKO ist defekt", "Kondensator nochmal prüfen?") == [
        "kondensator",
        "elko",
        "defekt",
        "nochmal",
        "prüfen",
    ]


def test_extract_keywords_no_short_words():
    assert extract_keywords("a b c", "Was tun?") == []


def test_extract_keywords_max_six():
    words = extract_keywords("eins zwei drei vier fünf sechs sieben")
    assert len(words) == 6


# ---------- Reine Funktion build_context ----------

def test_build_context_full_structure(tmp_db):
    device_id, ticket_id = seed_ticket_with_journal(tmp_db)
    other_id = seed_other_repair(tmp_db)
    tmp_db.execute(
        "INSERT INTO documents (device_id, ticket_id, title, doc_type, text_content)"
        " VALUES (?, ?, 'Datenblatt PS-123', 'datasheet', ?)",
        (device_id, ticket_id, "X" * 500),
    )
    tmp_db.commit()

    ctx = build_context(tmp_db, ticket_id, QUESTION)
    lines = ctx.split("\n")

    assert lines[0] == (
        "GERÄT: Netzteil Voltcraft (Netzteil), Hersteller Voltcraft, Modell PS-123"
    )
    assert lines[1] == "FEHLER: Netzteil tot"
    assert lines[2] == "STATUS: in_arbeit"
    assert lines[3] == "SCHON ERLEDIGT (nicht wieder vorschlagen):"
    assert lines[-1] == "FRAGE DES NUTZERS: Was tun?"

    # Nur die letzten 10 Einträge, chronologisch aufsteigend
    journal_lines = [l for l in lines if l.startswith("  [")]
    assert len(journal_lines) == 10
    assert "Schritt 1:" not in ctx
    assert "Schritt 2:" not in ctx
    assert "Schritt 3:" in ctx
    assert "Schritt 12:" in ctx
    assert "10:03:00" in journal_lines[0]
    assert "10:12:00" in journal_lines[-1]
    # Author vorhanden / None → —
    assert any("Max: Schritt 3:" in l for l in journal_lines)
    assert any("—: Schritt 4:" in l for l in journal_lines)

    # FTS-Treffer nur aus anderem Ticket
    hits = [l for l in lines if l.startswith("  Ticket #")]
    assert hits == [
        f"  Ticket #{other_id}, Verstärker Marantz: "
        "Kondensator im Netzteil Elko aufgequollen, getauscht"
    ]
    assert f"Ticket #{ticket_id}," not in ctx

    # Dokument auf 400 Zeichen gekürzt
    assert f"  Datenblatt PS-123 (datasheet): {'X' * 400}" in lines


def test_build_context_joins_keywords_with_or(tmp_db, monkeypatch):
    import app.context_builder as cb

    queries = []

    def fake_search(conn, query, limit=20):
        queries.append(query)
        return {"journal": [], "documents": []}

    monkeypatch.setattr(cb, "search", fake_search)
    _device_id, ticket_id = seed_ticket_with_journal(tmp_db)

    build_context(tmp_db, ticket_id, "Was tun?")
    assert queries[-1] == "netzteil"

    build_context(tmp_db, ticket_id, "Elko geplatzt?")
    # search() übernimmt jetzt die OR-Verknüpfung; Übergabe ist leerzeichen-getrennt
    assert queries[-1] == "netzteil elko geplatzt"


def test_build_context_no_keywords_skips_search(tmp_db, monkeypatch):
    import app.context_builder as cb

    def fail_search(conn, query, limit=20):
        raise AssertionError("search sollte nicht aufgerufen werden")

    monkeypatch.setattr(cb, "search", fail_search)
    cur = tmp_db.execute("INSERT INTO devices (name) VALUES ('Toaster')")
    device_id = cur.lastrowid
    cur = tmp_db.execute(
        "INSERT INTO tickets (device_id, fault_description) VALUES (?, 'tot')",
        (device_id,),
    )
    ticket_id = cur.lastrowid
    tmp_db.commit()

    ctx = build_context(tmp_db, ticket_id, "Hm?")
    assert "  (keine Treffer)" in ctx


def test_build_context_splits_done_vs_open(tmp_db):
    """Deterministischer Split: schritt/ersatzteil/ergebnis → SCHON ERLEDIGT
    (Modell darf sie nicht mehr vorschlagen), diagnose/notiz → OFFENE BEFUNDE.
    Regression: Assistent schlug wiederholt Erledigtes vor (Wahlschalter!)."""
    from app.context_builder import build_context as bc

    cur = tmp_db.execute("INSERT INTO devices (name) VALUES ('Toaster')")
    device_id = cur.lastrowid
    cur = tmp_db.execute(
        "INSERT INTO tickets (device_id, fault_description) VALUES (?, 'tot')",
        (device_id,),
    )
    ticket_id = cur.lastrowid
    rows = [
        ("schritt", "Schrauben mit Dreikant geöffnet", "2026-08-01 10:01:00"),
        ("diagnose", "Netzteil-Elko aufgequollen", "2026-08-01 10:02:00"),
        ("ersatzteil", "Ersatzteil bestellt", "2026-08-01 10:03:00"),
        ("ergebnis", "Erneuter Funktionstest bestanden", "2026-08-01 10:04:00"),
        ("notiz", "Kunde fragt nach Kosten", "2026-08-01 10:05:00"),
    ]
    for entry_type, content, created_at in rows:
        tmp_db.execute(
            "INSERT INTO journal_entries (ticket_id, author, entry_type, content, created_at)"
            " VALUES (?, 'Max', ?, ?, ?)",
            (ticket_id, entry_type, content, created_at),
        )
    tmp_db.commit()

    ctx = bc(tmp_db, ticket_id, "Was fehlt noch?")
    assert "SCHON ERLEDIGT (nicht wieder vorschlagen):" in ctx
    assert "OFFENE BEFUNDE (darauf aufbauen):" in ctx
    # Erledigtes in der Erledigt-Sektion, offenes in der Befund-Sektion
    done = ctx.split("OFFENE BEFUNDE")[0]
    open_f = ctx.split("OFFENE BEFUNDE")[1]
    for done_txt in ("Schrauben", "Ersatzteil bestellt", "Funktionstest"):
        assert done_txt in done
        assert done_txt not in open_f
    for open_txt in ("aufgequollen", "Kosten"):
        assert open_txt in open_f
        assert open_txt not in done


def test_build_context_empty_sections(tmp_db):
    cur = tmp_db.execute("INSERT INTO devices (name) VALUES ('Toaster')")
    device_id = cur.lastrowid
    cur = tmp_db.execute(
        "INSERT INTO tickets (device_id, fault_description) VALUES (?, 'Heizt nicht')",
        (device_id,),
    )
    ticket_id = cur.lastrowid
    tmp_db.commit()

    ctx = build_context(tmp_db, ticket_id, "Was tun?")
    assert "GERÄT: Toaster (—), Hersteller —, Modell —" in ctx
    assert "SCHON ERLEDIGT" in ctx
    assert "OFFENE BEFUNDE" in ctx
    assert "  (noch nichts abgeschlossen)" in ctx
    assert "  (keine Treffer)" in ctx
    assert "  (keine)" in ctx


def test_build_context_document_without_text(tmp_db):
    cur = tmp_db.execute("INSERT INTO devices (name) VALUES ('Toaster')")
    device_id = cur.lastrowid
    cur = tmp_db.execute(
        "INSERT INTO tickets (device_id, fault_description) VALUES (?, 'Heizt nicht')",
        (device_id,),
    )
    ticket_id = cur.lastrowid
    tmp_db.execute(
        "INSERT INTO documents (device_id, ticket_id, title, doc_type)"
        " VALUES (?, ?, 'Schaltplan', 'schema')",
        (device_id, ticket_id),
    )
    tmp_db.commit()

    ctx = build_context(tmp_db, ticket_id, "Was tun?")
    assert "  Schaltplan (schema): kein Text extrahiert" in ctx


def test_build_context_respects_max_chars(tmp_db):
    device_id, ticket_id = seed_ticket_with_journal(tmp_db)
    seed_other_repair(tmp_db)
    tmp_db.execute(
        "INSERT INTO documents (device_id, ticket_id, title, doc_type, text_content)"
        " VALUES (?, ?, 'Datenblatt', 'datasheet', ?)",
        (device_id, ticket_id, "Y" * 800),
    )
    tmp_db.commit()

    ctx = build_context(tmp_db, ticket_id, QUESTION, max_chars=300)

    assert len(ctx) <= 300
    # Kopf bleibt vollständig
    assert ctx.startswith("GERÄT: Netzteil Voltcraft (Netzteil), Hersteller Voltcraft, Modell PS-123\n")
    assert "FEHLER: Netzteil tot" in ctx
    assert "STATUS: in_arbeit" in ctx
    # Frage-Zeile bleibt vollständig
    assert ctx.endswith("FRAGE DES NUTZERS: Was tun?")


def test_build_context_missing_ticket_raises(tmp_db):
    with pytest.raises(ValueError):
        build_context(tmp_db, 9999, "Was tun?")