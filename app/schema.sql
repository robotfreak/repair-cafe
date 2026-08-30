CREATE TABLE IF NOT EXISTS devices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  category TEXT,
  manufacturer TEXT,
  model TEXT,
  serial_number TEXT,
  owner_name TEXT,
  owner_contact TEXT,
  accessories TEXT,
  schutzklasse TEXT CHECK(schutzklasse IS NULL OR schutzklasse IN ('I','II','III')),
  heating_kw REAL CHECK(heating_kw IS NULL OR heating_kw > 0),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS test_devices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  serial_number TEXT,
  calibration_until TEXT,
  notes TEXT,
  archived INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS equipment_tests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL UNIQUE REFERENCES tickets(id),
  protection_class TEXT NOT NULL CHECK(protection_class IN ('I','II','III')),
  heating_kw REAL,
  measurements TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK(verdict IN ('bestanden','nicht_bestanden')),
  tester TEXT,
  notes TEXT,
  test_device_id INTEGER REFERENCES test_devices(id),
  test_device_snapshot TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id INTEGER NOT NULL REFERENCES devices(id),
  status TEXT NOT NULL DEFAULT 'offen' CHECK(status IN
    ('offen','in_arbeit','erfolgreich','nicht_reparierbar','abgeholt')),
  fault_description TEXT NOT NULL,
  assignee TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  started_at TEXT,
  finished_at TEXT,
  picked_up_at TEXT,
  outcome_notes TEXT
);

CREATE TABLE IF NOT EXISTS waivers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL UNIQUE REFERENCES tickets(id),
  waiver_version TEXT NOT NULL,
  signed_name TEXT NOT NULL,
  accepted INTEGER NOT NULL CHECK(accepted = 1),
  signature_path TEXT,
  signed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS journal_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL REFERENCES tickets(id),
  author TEXT,
  entry_type TEXT NOT NULL DEFAULT 'notiz' CHECK(entry_type IN
    ('notiz','diagnose','schritt','ersatzteil','ergebnis')),
  content TEXT NOT NULL,
  edited_at TEXT,
  edited_by TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id INTEGER REFERENCES devices(id),
  ticket_id INTEGER REFERENCES tickets(id),
  title TEXT NOT NULL,
  doc_type TEXT NOT NULL DEFAULT 'datasheet' CHECK(doc_type IN
    ('datasheet','manual','schema','foto','sonstiges')),
  url TEXT,
  file_path TEXT,
  text_content TEXT,
  content_hash TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS journal_fts USING fts5(content, entry_type);
CREATE VIRTUAL TABLE IF NOT EXISTS doc_fts USING fts5(title, text_content);

CREATE TRIGGER IF NOT EXISTS journal_ai AFTER INSERT ON journal_entries BEGIN
  INSERT INTO journal_fts(rowid, content, entry_type)
  VALUES (new.id, new.content, new.entry_type);
END;
CREATE TRIGGER IF NOT EXISTS journal_au AFTER UPDATE ON journal_entries BEGIN
  DELETE FROM journal_fts WHERE rowid = old.id;
  INSERT INTO journal_fts(rowid, content, entry_type)
  VALUES (new.id, new.content, new.entry_type);
END;
CREATE TRIGGER IF NOT EXISTS journal_ad AFTER DELETE ON journal_entries BEGIN
  DELETE FROM journal_fts WHERE rowid = old.id;
END;
CREATE TRIGGER IF NOT EXISTS doc_ai AFTER INSERT ON documents BEGIN
  INSERT INTO doc_fts(rowid, title, text_content)
  VALUES (new.id, new.title, COALESCE(new.text_content,''));
END;
CREATE TRIGGER IF NOT EXISTS doc_au AFTER UPDATE ON documents BEGIN
  DELETE FROM doc_fts WHERE rowid = old.id;
  INSERT INTO doc_fts(rowid, title, text_content)
  VALUES (new.id, new.title, COALESCE(new.text_content,''));
END;
CREATE TRIGGER IF NOT EXISTS doc_ad AFTER DELETE ON documents BEGIN
  DELETE FROM doc_fts WHERE rowid = old.id;
END;