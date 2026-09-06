# 📱 Tablet im Repair-Koffer — Setup & Betrieb

**Standard-Gerät für digitale Dokumentation im Repair-Café**

---

## 🎯 **ZWECK**

Das Tablet dient als **zentrales Interface** für:

- ✅ **Repair-Café Software** anzeigen (Laufzettel, Board, Statistiken)
- ✅ **Messgeräte verwalten** (UT-501, Multimeter, Werkzeug)
- ✅ **Dokumente öffnen** (Handbücher, Anleitungen, Schaltpläne)
- ✅ **Workshops dokumentieren** (Schüler, Klassen, Ergebnisse)
- ✅ **BUND-Präsentationen** (Live-Demo der Software)

---

## 📦 **IM REPAIR-KOFFER ENTHALTEN**

| Komponente | Beschreibung |
|------------|--------------|
| **Tablet** | Android-Tablet (10-12 Zoll, mind. 4GB RAM) |
| **Fully Browser** | App für Vollbild-Anzeige mit Dark-Mode |
| **Tablet-Halterung** | Verstellbar, rutschfest |
| **USB-Ladekabel** | Mind. 2m für flexible Positionierung |
| **Powerbank** | Optional für mobilen Einsatz |

---

## 🔧 **FULLY BROWSER SETUP**

### **1. App installieren:**

```
Google Play Store → "Fully Kiosk Browser" installieren
```

**Kosten:**
- **Basic:** Kostenlos (reicht völlig!)
- **Premium:** ~5€ (unnötige Features)

---

### **2. Dark Mode erzwingen:**

**WICHTIG:** Auto-Dark-Mode funktioniert nicht zuverlässig!

**Einstellungen → Erweitert → WebView-Einstellungen:**
- ✅ **"Dark-Modus erzwingen"** aktivieren

**Alternativ (wenn obiges nicht reicht):**

**Einstellungen → Web-Inhalt → Benutzer-CSS injizieren:**

```css
:root {
  --bg: #191817 !important;
  --card: #232120 !important;
  --foreground: #ece9e4 !important;
  --muted-foreground: #a8a49c !important;
  --accent: #e5874e !important;
  --border: #3a3733 !important;
  --danger: #e5695f !important;
  --success: #7fc38a !important;
}
```

---

### **3. Startseite einrichten:**

**Einstellungen → Web-Inhalt → Startseite:**
```
http://localhost:5002
```

Oder für Netzwerk-Zugriff:
```
http://raspi500.local:5002
```

Oder mit fester IP:
```
http://192.168.1.100:5002
```

---

### **4. Vollbild-Modus:**

**Einstellungen → Layout & Vollbild:**
- ✅ **"Vollbildmodus"** aktivieren
- ✅ **Statusleiste ausblenden**
- ✅ **Navigationsleiste ausblenden**
- ✅ **Immersiver Modus** aktivieren

---

### **5. Touch-Optimierung:**

**Einstellungen → Touch-Eingabe:**
- ✅ **"Touch-Verzögerung"** auf 0ms setzen
- ✅ **"Double-Tap to Zoom"** deaktivieren (verhindert versehentliches Zoomen)

---

## 🔗 **REPAIR-CAFÉ URLS ALS FAVORITEN**

| URL | Beschreibung |
|-----|--------------|
| `http://localhost:5002/#/board` | **Board** — Alle Laufzettel |
| `http://localhost:5002/#/devices` | **Geräte** — Kunden-Geräte |
| `http://localhost:5002/#/test-devices` | **Messgeräte** — UT-501, Werkzeug |
| `http://localhost:5002/#/search` | **Suche** — Tickets durchsuchen |

---

## 🎯 **WORKFLOW IM REPAIR-CAFÉ**

### **Bei Geräte-Annahme:**

1. **Tablet einschalten** (Fully Browser startet automatisch)
2. **"Neuer Laufzettel"** tippen
3. **Gerät auswählen** (oder neu anlegen)
4. **Fehlerbeschreibung** eingeben
5. **Schutzklasse** setzen (I, II, oder III)
6. **Laufzettel speichern** → Gerät erscheint im Board

---

### **Während Reparatur:**

1. **Laufzettel im Board** antippen
2. **Status ändern** → "In Arbeit"
3. **Diagnose** eintragen (z.B. "Kabelbruch entdeckt")
4. **Schritte** dokumentieren (z.B. "Kabel angelötet")
5. **Ergebnis** festhalten (z.B. "Funktionsprüfung bestanden")

---

### **Isolationsprüfung (UT-501):**

1. **Im Laufzettel** → "Isolationsprüfung" Button
2. **Messgerät wählen** → "UNI-T UT-501"
3. **Prüfung durchführen** (siehe Checkliste)
4. **Messwerte eintragen**
5. **"Prüfung speichern"** → Protokoll wird angehängt

---

### **Gerät zurückgeben:**

1. **Status ändern** → "Erledigt" oder "Nicht reparierbar"
2. **Laufzettel ausdrucken** (optional)
3. **Gerät kennzeichnen** (mit Laufzettel-Nummer)

---

## 🎯 **WORKFLOW FÜR SCHUL-WORKSHOPS**

### **Vorbereitung:**

1. **Tablet laden** (100% Akku)
2. **Fully Browser starten**
3. **Demo-Daten laden** (für BUND-Präsentation)
4. **12 Lampen-Tickets** vorbereiten (alle "erfolgreich")

---

### **Während Workshop:**

1. **Schüler-Gruppen** einteilen (12 Gruppen à 3 Schüler)
2. **Jede Gruppe bekommt** eine Lampe + Laufzettel-Nummer
3. **Tablet rumgeben** → Jede Gruppe trägt ein:
   - Diagnose
   - Fehlersuche
   - Reparatur-Schritte
   - Ergebnis

---

### **Nach Workshop:**

1. **Statistik anzeigen** (alle 12 Lampen repariert)
2. **Erfolgsquote** feiern (100%!)
3. **Tablet für nächste Gruppe** zurücksetzen

---

## 📊 **STATISTIKEN ANZEIGEN**

**Im Browser:**

```
http://localhost:5002/#/board
```

**Zeigt:**
- ✅ **Offen** — Anzahl offener Laufzettel
- ✅ **In Arbeit** — Aktuelle Reparaturen
- ✅ **Erledigt heute** — Erfolgreiche Reparaturen
- ✅ **Abzuholen** — Fertige Geräte

---

## 🎯 **BUND-PRÄSENTATION (22.09.2026)**

### **Live-Demo mit Tablet:**

1. **Tablet einschalten** (Fully Browser im Dark-Mode)
2. **Board zeigen** (12 erfolgreiche Lampen-Reparaturen)
3. **Messgeräte Tab** öffnen (UT-501, Multimeter, Werkzeug)
4. **Ein Gerät anklicken** → Details aufklappen
5. **Dokumente zeigen** (Handbücher verlinkt)
6. **Bearbeiten demonstrieren** (Name ändern, speichern)

---

### **Präsentations-Folien:**

**Folie 12 (Erfolgs-Statistik):**
```
Workshop am 22.09.2026
Schule: Muster-Gymnasium
Klassen: 7a, 7b, 7c, 8a

Teilnehmer: 20 Schüler
Gruppen: 12
Repariert: 12/12 Lampen (100% ✅)

Durchschnittszeit: 45 Minuten

Häufigster Fehler: Kabelbruch
```

**Tablet zeigt LIVE die echten Daten!** 📊

---

## 🔧 **TROUBLESHOOTING**

### **Problem: Dark-Mode nicht aktiv**

**Lösung:**
```
Fully Einstellungen → Erweitert → WebView-Einstellungen
→ "Dark-Modus erzwingen" aktivieren
```

---

### **Problem: Tablet verbindet sich nicht**

**Lösung:**
1. **Pi500 im selben Netzwerk?**
2. **IP-Adresse prüfen:** `hostname -I`
3. **Firewall prüfen:** `sudo ufw status`
4. **Port 5002 freigegeben?** `sudo ufw allow 5002`

---

### **Problem: Touch zu empfindlich**

**Lösung:**
```
Fully Einstellungen → Touch-Eingabe
→ "Touch-Verzögerung" auf 100ms setzen
```

---

### **Problem: Akku hält nicht lang**

**Lösung:**
- ✅ **Helligkeit reduzieren** (50% reicht)
- ✅ **WLAN anlassen** (spart mehr als Flugmodus)
- ✅ **Powerbank anschließen** (10.000mAh = 2x voller Laden)

---

## 📦 **PACKLISTE FÜR WORKSHOPS**

```
□ Tablet (100% geladen)
□ Fully Browser gestartet
□ Tablet-Halterung
□ USB-Ladekabel (2m)
□ Powerbank (optional)
□ Reinigungstuch (Fingerabdrücke)
□ Backup: Zweites Tablet (falls vorhanden)
```

---

## 🎯 **CHECKLISTE — TABLET FERTIG FÜR WORKSHOP**

```
□ Fully Browser installiert
□ Dark-Mode erzwungen
□ Startseite: http://localhost:5002
□ Vollbild-Modus aktiv
□ Touch-Optimierung gesetzt
□ Alle Favoriten angelegt
□ Demo-Daten geladen (12 Lampen)
□ Tablet geladen (100%)
□ Halterung montiert
□ Kabel verstaut
```

---

## 🔗 **LINKS**

### **Interne Dokumente:**

- [Repair-Café Software](http://localhost:5002/)
- [Messgeräte-Übersicht](file:///home/pi/repair-cafe/docs/REPAIR-KOFFER-UEBERSICHT.md)
- [UNI-T UT-501 Anleitung](file:///home/pi/ki-os/vault/10-Projekte/080-Reparatur-Koffer/UNI-T-UT501-Anleitung.md)

### **Externe Ressourcen:**

- [Fully Browser Dokumentation](https://www.fully-kiosk.com/de/)
- [Android Dark-Mode Guide](https://developer.android.com/guide/topics/ui/look-and-feather/darktheme)

---

## 📊 **TABLET ALS MESSGERÄT IM SYSTEM**

Das Tablet ist im Repair-Café System als **Gerät** registriert:

- **Name:** Tablet (Fully Browser)
- **Kategorie:** Digitale Dokumentation
- **Schutzklasse:** III (Schutzkleinspannung, USB 5V)
- **Zubehör:** Halterung, Kabel, Fully Browser App

**NICHT als Messgerät** (ID: 2-6) — das Tablet ist ein **Anzeige-Gerät**!

---

**Version:** 2026-09-06  
**Für:** Repair-Café & Schul-Workshops  
**Status:** ✅ Tablet als Standard-Gerät im Koffer

---

*Tablet gehört fest zum Repair-Koffer wie UT-501 und Werkzeug!* 🔧📱✨
