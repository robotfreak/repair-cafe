"""Grenzwerte für Prüfungen nach DIN VDE 0701-0702 / DGUV Vorschrift 3.

Reiner Katalog + Bewertungslogik (kein Flask, keine DB) — die API liefert
daraus die Checkliste am Laufzettel und bewertet Messwerte serverseitig,
damit UI und Speicherung identische Regeln haben.

Quellen: DIN VDE 0701-0702:2020 (Grenzwerttabellen für Instandsetzung/
Wiederholungsprüfung ortsveränderlicher Geräte), DGUV Vorschrift 3 § 5
(Prüffristen-Richtwerte). Werte sind technisch, keine Rechtsberatung.
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


def checks_for(protection_class, heating_kw=None):
    """Prüfpflichtige Posten je Schutzklasse als Liste von Dicts.

    heating_kw (nur SK I relevant) schärft die Grenzwerte für Geräte mit
    Heizelementen: Isolation 0,3 MΩ statt 1,0 MΩ; Schutzleiterstrom
    1 mA/kW begrenzt auf 10 mA statt pauschal 3,5 mA.
    """
    if protection_class not in PROTECTION_CLASSES:
        raise ValueError(f"Unbekannte Schutzklasse: {protection_class!r}")

    checks = [_boolean(
        "besichtigung",
        "Besichtigung: Gehäuse, Leitung, Stecker, Schalter unbeschädigt")]

    if protection_class == "I":
        checks.append(_numeric(
            "schutzleiter", "Schutzleiterwiderstand", "Ω", "max",
            SCHUTZLEITER_MAX_OHM,
            "bis 5 m Leitungslänge und 16 A; je weitere 5 m +0,1 Ω, max. 1,0 Ω"))
        iso = ISOLATION_MIN_MOHM["I_heiz"] if heating_kw else ISOLATION_MIN_MOHM["I"]
        checks.append(_numeric(
            "isolation", "Isolationswiderstand (500 V DC)", "MΩ", "min", iso))
        if heating_kw:
            limit = round(min(HEIZELEMENT_MA_PRO_KW * heating_kw, HEIZELEMENT_MA_CAP), 2)
            hint = f"1 mA/kW bei {heating_kw:g} kW, absolut max. {HEIZELEMENT_MA_CAP:g} mA"
        else:
            limit = SCHUTZLEITERSTROM_MAX_MA
            hint = None
        checks.append(_numeric(
            "schutzleiterstrom", "Schutzleiterstrom", "mA", "max", limit, hint))
        checks.append(_numeric(
            "beruehrungsstrom", "Berührungsstrom (nicht mit PE verbundene Teile)",
            "mA", "max", BERUEHRUNGSSTROM_MAX_MA))
    else:
        checks.append(_numeric(
            "isolation", "Isolationswiderstand (500 V DC)", "MΩ", "min",
            ISOLATION_MIN_MOHM[protection_class]))
        if protection_class == "II":
            checks.append(_numeric(
                "beruehrungsstrom", "Berührungsstrom", "mA", "max",
                BERUEHRUNGSSTROM_MAX_MA))

    checks.append(_boolean("funktion", "Funktionsprüfung nach der Prüfung"))
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