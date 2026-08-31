"""Kontext-Builder für den Reparatur-Assistenten (Task 8).

Reine Funktion ohne Flask-Abhängigkeit: sammelt Ticket, Gerät,
Tagebuch-Einträge, FTS-Treffer aus früheren Reparaturen und Dokumente
und baut daraus einen gekürzten deutschen Kontext-String für das LLM.
"""
from app.search import search

MAX_KEYWORDS = 6
MIN_WORD_LEN = 4
HITS_MAX = 3
DOCS_MAX = 3
JOURNAL_MAX = 10
SNIPPET_MAX = 200
DOC_TEXT_MAX = 400
# Diese Eintragstypen sind abgeschlossene Arbeiten — sie landen in
# SCHON ERLEDIGT, damit das Modell sie nicht erneut vorschlägt.
# diagnose/notiz sind Befunde/Offenpunkte → OFFENE BEFUNDE.
DONE_TYPES = ("schritt", "ersatzteil", "ergebnis")


def extract_keywords(*texts):
    """Einfache Schlüsselwörter aus Texten: >=4 Zeichen, lowercase, dedupliziert, max 6."""
    words = []
    for text in texts:
        for raw in str(text or "").split():
            cleaned = "".join(ch for ch in raw if ch.isalnum()).lower()
            if len(cleaned) >= MIN_WORD_LEN and cleaned not in words:
                words.append(cleaned)
    return words[:MAX_KEYWORDS]


def _trunc(text, limit):
    text = text or ""
    return text[:limit]


def _format_journal_line(entry):
    author = entry["author"] or "—"
    return f"  [{entry['entry_type']}] {entry['created_at']} {author}: {entry['content']}"


def _format_hit_line(hit):
    return f"  Ticket #{hit['ticket_id']}, {hit['device_name']}: {_trunc(hit['snippet'], SNIPPET_MAX)}"


def _format_doc_line(title, doc_type, text_content):
    if text_content is None:
        return f"  {title} ({doc_type}): kein Text extrahiert"
    return f"  {title} ({doc_type}): {_trunc(text_content, DOC_TEXT_MAX)}"


def build_context(conn, ticket_id, question, max_chars=6000):
    """Baut den deutschen Kontext-String für den Assistenten.

    Wirft ValueError('ticket not found'), wenn der Laufzettel fehlt.
    Bei Überschreitung von max_chars werden Mittelteile von hinten
    entfernt (erst DOKUMENTE-Zeilen, dann Suchtreffer, dann älteste
    Tagebuch-Einträge); Kopf und FRAGE-Zeile bleiben immer vollständig.
    """
    row = conn.execute(
        "SELECT t.*, d.name AS device_name, d.category, d.manufacturer, d.model"
        " FROM tickets t JOIN devices d ON d.id = t.device_id WHERE t.id = ?",
        (ticket_id,),
    ).fetchone()
    if row is None:
        raise ValueError("ticket not found")

    head = [
        f"GERÄT: {row['device_name']} ({row['category'] or '—'}),"
        f" Hersteller {row['manufacturer'] or '—'}, Modell {row['model'] or '—'}",
        f"FEHLER: {row['fault_description']}",
        f"STATUS: {row['status']}",
    ]

    # 2. Letzte 10 Tagebuch-Einträge (chronologisch aufsteigend), deterministisch
    #    gesplittet: erledigte Arbeiten vs. offene Befunde — das Modell soll
    #    Erledigtes nicht mehr als Vorschlag rezitieren (Regression).
    entries = conn.execute(
        "SELECT * FROM journal_entries WHERE ticket_id = ?"
        " ORDER BY created_at DESC, id DESC LIMIT ?",
        (ticket_id, JOURNAL_MAX),
    ).fetchall()
    entries_asc = list(reversed(entries))
    done_lines = [
        _format_journal_line(e) for e in entries_asc if e["entry_type"] in DONE_TYPES
    ]
    open_lines = [
        _format_journal_line(e) for e in entries_asc if e["entry_type"] not in DONE_TYPES
    ]

    # 3. FTS-Suche über frühere Reparaturen (aktuelles Ticket ausgeschlossen)
    keywords = extract_keywords(row["fault_description"], question)
    hit_lines = []
    if keywords:
        # search() verknüpft alle Begriffe per OR (siehe docstring dort)
        result = search(conn, " ".join(keywords))
        for hit in result["journal"]:
            if hit["ticket_id"] == ticket_id:
                continue
            hit_lines.append(_format_hit_line(hit))
            if len(hit_lines) >= HITS_MAX:
                break

    # 4. Dokumente zum Gerät oder Ticket
    doc_rows = conn.execute(
        "SELECT title, doc_type, text_content FROM documents"
        " WHERE device_id = ? OR ticket_id = ? LIMIT ?",
        (row["device_id"], ticket_id, DOCS_MAX),
    ).fetchall()
    doc_lines = [_format_doc_line(d["title"], d["doc_type"], d["text_content"]) for d in doc_rows]

    tail = [f"FRAGE DES NUTZERS: {question}"]

    def journal_sections(done, open_f):
        return [
            (
                "SCHON ERLEDIGT (nicht wieder vorschlagen):",
                done if done else ["  (noch nichts abgeschlossen)"],
            ),
            (
                "OFFENE BEFUNDE (darauf aufbauen):",
                open_f if open_f else ["  (keine offenen Befunde)"],
            ),
        ]

    def assemble(journal, hits, docs):
        parts = list(head)
        for label, lines in journal_sections(*journal):
            parts.append(label)
            parts.extend(lines)
        parts.append("FRÜHERE REPARATUREN (Suchtreffer):")
        parts.extend(hits if hits else ["  (keine Treffer)"])
        parts.append("DOKUMENTE:")
        parts.extend(docs if docs else ["  (keine)"])
        parts.extend(tail)
        return "\n".join(parts)

    n_headers = 4  # 2 Journal-Sektionen + Suchtreffer + Dokumente
    total = len("\n".join(head)) + 1 + len("\n".join(tail)) + n_headers
    if total > max_chars:
        # Kopf+Frage allein passen nicht: Header und Platzhalter fallen mit.
        return "\n".join(head + tail)

    context = assemble((done_lines, open_lines), hit_lines, doc_lines)
    if len(context) <= max_chars:
        return context

    # Mittelteile von hinten droppen: erst Dokumente, dann Suchtreffer,
    # dann älteste offene Befunde, dann älteste erledigte Schritte.
    # ERLEDIGT bleibt so lange wie möglich — es ist der Anti-Wiederholungsschutz.
    docs, hits = list(doc_lines), list(hit_lines)
    done, open_f = list(done_lines), list(open_lines)
    while len(assemble((done, open_f), hits, docs)) > max_chars:
        if docs:
            docs.pop()
        elif hits:
            hits.pop()
        elif open_f:
            open_f.pop(0)
        elif done:
            done.pop(0)
        else:
            break
    final = assemble((done, open_f), hits, docs)
    if len(final) > max_chars:
        # Extremfall: selbst leere Sektionen mit Platzhaltern passen nicht
        # (sehr kleines max_chars) → nur Kopf+Frage.
        return "\n".join(head + tail)
    return final