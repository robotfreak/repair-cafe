def test_init_creates_all_tables(tmp_db):
    tables = {r["name"] for r in tmp_db.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','trigger')")}
    assert {"devices","tickets","waivers","journal_entries","documents",
            "journal_fts","doc_fts","journal_ai","doc_ai"} <= tables

def test_wal_mode(tmp_db):
    assert tmp_db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"

def test_health(app_client):
    assert app_client.get("/api/health").get_json() == {"ok": True}

def test_init_db_is_idempotent(tmp_path):
    """Regression: zweiter create_app/init_db-Aufruf auf derselben DB darf nicht crashen."""
    from app import create_app
    db_path = str(tmp_path / "repair.db")
    create_app(data_dir=str(tmp_path))
    create_app(data_dir=str(tmp_path))  # zweiter Start: darf keinen Fehler werfen