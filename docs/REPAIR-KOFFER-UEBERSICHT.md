# 🛠️ Repair-Koffer — Messgeräte & Werkzeug

**Integriert ins Repair-Café System**

---

## 📊 MESSGERÄTE IM SYSTEM

Alle Messgeräte sind im Repair-Café System unter `/api/test-devices` registriert:

| ID | Name | Typ | Notes |
|----|------|-----|-------|
| **2** | UNI-T UT-501 | Isolationsprüfgerät | 500V DC, nicht VDE-konform |
| **4** | Multimeter Digital (Koffer) | Universal-Multimeter | Durchgang, Spannung, Widerstand |
| **5** | Lötkolben 25W (Koffer) | Werkzeug | Elektronik-Reparaturen |
| **6** | Werkzeug-Set (Koffer) | Werkzeug-Set | Schraubendreher, Zangen, etc. |

---

## 📖 HANDBÜCHER & ANLEITUNGEN

### **Im Vault gespeichert:**

**Lehrer-Handbücher:**
- [Workshop-Anleitung für Lehrer](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Workshop-Anleitung-Lehrer.md)
- [Lösungsblatt (NUR für Lehrer)](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Loesungsblatt-Lehrer.md)

**Arbeitsblätter:**
- [Arbeitsblatt 1: Funktionsweise](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Arbeitsblatt-01-Funktionsweise.md)
- [Arbeitsblatt 2: Fehler-Checkliste](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Arbeitsblatt-02-Fehler-Checkliste.md)
- [Arbeitsblatt 3: Reparatur-Doku](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Arbeitsblatt-03-Reparatur-Doku.md)

**Fach-Dokumentation:**
- [Fehler-Katalog (12 Lampen)](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Fehler-Katalog-12-Lampen.md)
- [UNI-T UT-501/UT-510 Bedienanleitung](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/UNI-T-UT501-Anleitung.md)
- [Material für BUND-Präsentation](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Material-BUND-Praesentation.md)
- [Präsentations-Folien](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Praesentation-BUND-2026-09-22.md)
- [Schul-Konfiguration Software](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Schul-Konfiguration-Software.md)

---

## 🔧 MESSGERÄTE IM DETAIL

### **UNI-T UT-501 (ID: 2)**

**Spezifikation:**
- **Typ:** Isolationswiderstand-Tester
- **Prüfspannung:** 500V DC
- **Messbereich:** 0.01 MΩ … 2000 MΩ
- **Status:** Nicht VDE-konform (nur für Repair-Café intern)

**Einsatz:**
- Isolationsprüfung an Dynamo-Taschenlampen
- Schul-Workshops (ab Klasse 5)
- Repair-AGs an Schulen

**Anleitung:** → [UNI-T UT-501 Bedienanleitung](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/UNI-T-UT501-Anleitung.md)

---

### **Multimeter Digital (ID: 4)**

**Spezifikation:**
- **Typ:** Digital-Multimeter
- **Funktionen:** 
  - Durchgangsprüfung (piept bei Kontakt)
  - Spannung messen (DC/AC)
  - Widerstand messen
  - Strom messen
- **Status:** Im Repair-Koffer enthalten

**Einsatz:**
- Fehlersuche (Kabel, Kontakte, Schalter)
- Systematische Prüfung (siehe Arbeitsblatt 2)
- Für alle Klassenstufen

**Anleitung:** → [Fehler-Checkliste Arbeitsblatt 2](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Arbeitsblatt-02-Fehler-Checkliste.md)

---

### **Lötkolben 25W (ID: 5)**

**Spezifikation:**
- **Leistung:** 25W
- **Temperatur:** ca. 300-350°C
- **Status:** Im Repair-Koffer enthalten

**Einsatz:**
- Kabel anlöten
- LED tauschen
- Kondensatoren einsetzen
- Nur unter Aufsicht! (ab Klasse 7)

**Sicherheit:**
- 🔥 HEISS! Nur an Isolierung anfassen
- Nach Gebrauch in Halterung legen
- Raum lüften (Lötrauch!)

---

### **Werkzeug-Set (ID: 6)**

**Inhalt:**
- Schraubendreher (Kreuz + Schlitz, diverse Größen)
- Seitenschneider
- Spitzzange
- Pinzette
- Entlötpumpe
- Entlötlitze

**Status:** Im Repair-Koffer enthalten

**Einsatz:**
- Für alle Reparaturen
- Systematisch einsetzen (siehe Checklisten)
- Nach Gebrauch vollständig zurücklegen

---

## 📋 CHECKLISTEN

### **Vor Workshop-Beginn:**

```
□ Alle Messgeräte geladen/funktionsbereit?
□ Werkzeug vollständig?
□ Erste-Hilfe-Koffer griffbereit?
□ Sicherheits-Checklisten ausgedruckt?
□ Arbeitsblätter bereit?
□ Ersatzteile (LED, Kabel, Lötzinn)?
```

### **Nach Workshop:**

```
□ Alle Messgeräte gezählt?
□ Werkzeug vollständig?
□ Verbrauchsmaterial aufgefüllt?
□ Raum gelüftet?
□ Müll entsorgt?
```

---

## 🎯 REPAIR-KOFFER IM UNTERRICHT

### **Für Lehrer:**

**Vorbereitung:**
1. [Workshop-Anleitung lesen](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Workshop-Anleitung-Lehrer.md)
2. [Fehler-Katalog studieren](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Fehler-Katalog-12-Lampen.md)
3. Lampen präparieren (nach Katalog)
4. Werkzeug prüfen
5. Sicherheits-Checklisten ausdrucken

**Während Workshop:**
1. [Arbeitsblatt 1 austeilen](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Arbeitsblatt-01-Funktionsweise.md) (Einführung)
2. [Arbeitsblatt 2 austeilen](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Arbeitsblatt-02-Fehler-Checkliste.md) (Fehlersuche)
3. [Arbeitsblatt 3 austeilen](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Arbeitsblatt-03-Reparatur-Doku.md) (Dokumentation)
4. Herumgehen und helfen
5. [Lösungsblatt](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/Loesungsblatt-Lehrer.md) bereithalten (NICHT zeigen!)

**Nachbereitung:**
1. Erfolgsstatistik im Repair-Café System prüfen
2. Feedback auswerten
3. Nächstes Mal planen

---

## 📊 STATISTIKEN

### **Im Repair-Café System:**

```bash
# Alle Messgeräte anzeigen
curl http://localhost:5002/api/test-devices

# Tickets mit Prüfungen anzeigen
curl http://localhost:5002/api/tickets?include_tests=true

# Statistik für Schule
curl http://localhost:5002/api/school/statistics?school_name=Muster-Gymnasium
```

### **Typische Werte:**

| Workshop | Schüler | Reparaturen | Erfolgsquote | Ø Zeit |
|----------|---------|-------------|--------------|--------|
| **Test 05.09.** | 36 | 12 | 100% | 47 Min |
| **BUND 22.09.** | 20 | 12 | 100% | 45 Min |
| **Schule (geplant)** | 36 | 12 | 100% | 45 Min |

---

## 🔗 LINKS

### **Interne Dokumente:**

- [Repair-Café Software](http://localhost:5002/)
- [Web Dashboard](http://localhost:8050/)
- [Repair-cafe-school Repo](https://github.com/robotfreak/repair-cafe-school) (noch nicht erstellt)

### **Externe Ressourcen:**

- [UNI-T UT-501 Produktseite](https://www.uni-trend.com/productsdetail/98.html)
- [DIN VDE 0701-0702 (Referenz)](https://www.vde-verlag.de/normen/0413300/din-vde-0701-0702.html)
- [DGUV Vorschrift 3](https://www.dguv.de/medien/inhalt/dguvvorschriften/203-061.pdf)

---

## 📞 SUPPORT

**Bei Fragen zum Repair-Koffer:**

- Lehrer-Handbuch konsultieren
- Fehler-Katalog prüfen
- Im Repair-Café System nachsehen
- Lokales Repair-Café fragen

---

**Version:** 2026-09-06  
**Für:** Repair-Café & Schul-AGs  
**Status:** ✅ Alle Messgeräte im System registriert

---

*Alle Dokumente im Vault unter: `/home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/`*
