"""Grenzwerte für Prüfungen nach DIN VDE 0701-0702 / DGUV Vorschrift 3.

Reiner Katalog + Bewertungslogik (kein Flask, keine DB) — die API liefert
daraus die Checkliste am Laufzettel und bewertet Messwerte serverseitig,
damit UI und Speicherung identische Regeln haben.

Quellen: DIN VDE 0701-0702:2020 (Grenzwerttabellen für Instandsetzung/
Wiederholungsprüfung ortsveränderlicher Geräte), DGUV Vorschrift 3 § 5
(Prüffristen-Richtwerte). Werte sind technisch, keine Rechtsberatung.

HINWEIS: Seit 2026-09-05 verwenden wir statt VDE-konformer Prüfung eine
vereinfachte Isolationsprüfung mit UNI-T UT-501. Dies ist NICHT VDE-konform,
aber für Repair-Café Zwecke ausreichend (Haftungsausschluss beachten!).
"""

PROTECTION_CLASSES = ("I", "II", "III")

# Prüffrist-Richtwerte für ortsveränderliche Betriebsmittel (Monate);
# bei Fehlerquote < 2 % ist Verlängerung möglich (DGUV V3 § 5).
RETENTION_MONTHS = {
    "baustelle": 3,
    "werkstatt": 12,   # Fertigungsstätten, Werkstätten und ähnliche Bedingungen
    "buero": 24,       # Büros und ähnliche Bedingungen
}

SCHUTZLEITER_MAX_OHM = 0.3        # ≤ 0,3 Ω bis 5 m Leitungslänge, ≤ 16 A
ISOLATION_MIN_MOHM = {            # Mindest-Isolationswiderstand in MΩ
    "I": 1.0,
    "I_heiz": 0.3,                # SK I mit Heizelementen
    "II": 2.0,                    # Schutzisolierung
    "III": 0.25,                  # Schutzkleinspannung (250 kΩ)
}
SCHUTZLEITERSTROM_MAX_MA = 3.5    # Geräte allgemein
HEIZELEMENT_MA_PRO_KW = 1.0       # 1 mA/kW bei eingeschalteten Heizelementen
HEIZELEMENT_MA_CAP = 10.0         # absoluter Höchstwert
BERUEHRUNGSSTROM_MAX_MA = 0.5     # nicht mit PE verbundene berührbare Teile


def _numeric(key, label, unit, direction, limit, hint=None):
    return {"key": key, "label": label, "unit": unit, "direction": direction,
            "limit": limit, "hint": hint}


def _boolean(key, label, hint=None):
    return {"key": key, "label": label, "unit": None, "direction": "bool",
            "limit": None, "hint": hint}


def checks_for(protection_class, heating_kw=None, use_vde_conform=False, is_school_workshop=False):
    """Prüfpunkte je Schutzklasse.
    
    WICHTIG: UT-501 ist NUR für Leitungen/Kabel (NICHT für Geräte)!
    Für Geräte-Reparaturen (Repair-Café, Schulen):
    - NUR Besichtigung + Funktionsprüfung
    - Multimeter für Durchgang/Spannung (KEINE Isolationsprüfung!)
    
    is_school_workshop=True: KEINE Isolationsprüfung! (nur 5V-Geräte, SK III)
    """
    if protection_class not in PROTECTION_CLASSES:
        raise ValueError(f"Unbekannte Schutzklasse: {protection_class!r}")

    # FÜR ALLE GERÄTE: NUR Besichtigung + Funktion (KEINE Isolationsprüfung!)
    # UT-501 ist NUR für Leitungen/Kabel, NICHT für fertige Geräte!
    checks = [
        _boolean("besichtigung", "Besichtigung: Gehäuse, Leitung, Stecker, Schalter unbeschädigt"),
        _boolean("funktion", "Funktionsprüfung nach der Reparatur")
    ]
    return checks


def evaluate(check, value):
    """Bewertet einen eingegebenen Wert gegen den Grenzwert.

    Rückgabe: (ok: bool, fehlertext: str | None).
    """
    if check["direction"] == "bool":
        ok = value == "ok"
        return ok, None if ok else "als mangelhaft markiert"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return False, "kein gültiger Messwert"
    if num < 0:
        return False, "negativer Messwert unzulässig"
    if check["direction"] == "max":
        ok = num <= check["limit"]
    elif check["direction"] == "min":
        ok = num >= check["limit"]
    else:
        return False, "unbekannter Prüftyp"
    op = "≤" if check["direction"] == "max" else "≥"
    return ok, None if ok else (
        f"Grenzwert verletzt: {num:g} {check['unit']} (erlaubt {op} "
        f"{check['limit']:g} {check['unit']})")