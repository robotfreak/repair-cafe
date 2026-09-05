# UNI-T UT-501 Isolationsprüfgerät — Bedienanleitung

**Einsatz im Repair-Café** — Seit 2026-09-05

---

## ⚠️ SICHERHEITSHINWEISE

```
⚡  ACHTUNG: Netzspannung kann tödlich sein!
```

1. **Gerät NETZSTECKER ziehen** vor der Prüfung
2. **Kondensatoren entladen** (z.B. bei Netzteilen, Motoren)
3. **Nicht an unter Spannung stehenden Teilen messen**
4. **Trockene Hände und trockener Arbeitsplatz**
5. **Kinder und Laien fernhalten**

---

## 📦 GERÄTEBESCHREIBUNG

### **UNI-T UT-501 Isolationswiderstand-Tester**

| Feature | Wert |
|---------|------|
| **Messbereich** | 0.01 MΩ … 2000 MΩ |
| **Prüfspannung** | 500 V DC |
| **Anzeige** | Digital LCD |
| **Stromversorgung** | 6 × 1.5V AA Batterien |
| **Schutzklasse** | IP40 (spritzwassergeschützt) |

### **Bedienelemente:**

```
┌─────────────────────────────────┐
│  [POWER]  [HOLD]  [LIGHT]      │  ← Tasten
│                                 │
│       [ DREHSCHALTER ]          │  ← OFF / 500V
│                                 │
│  COM ────[BUCHSEN]──── 500V     │  ← Messleitungen
└─────────────────────────────────┘
```

---

## 🔧 VORBEREITUNG

### **1. Gerät einschalten:**
```
DREHSCHALTER auf "500V" drehen
→ Display zeigt "OL" (Over Limit / unendlich)
```

### **2. Messleitungen anschließen:**
```
SCHWARZE Leitung → COM (schwarze Buchse)
ROTE Leitung → 500V (rote Buchse)
```

### **3. Prüfling vorbereiten:**
```
□ Gerät vom Netz trennen (Stecker ziehen!)
□ Alle Schalter EIN (damit alle Teile geprüft werden)
□ Bei Motoren/Kondensatoren: Diese entladen
□ Stecker und Anschlüsse müssen trocken sein
```

---

## 📏 MESSDURCHFÜHRUNG

### **Schutzklasse I (Geräte mit Schutzleiter):**

**Messpunkt 1: L/PE (Außenleiter gegen Schutzleiter)**

```
1. ROTE Messspitze → L-Kontakt im Stecker (links bei Schuko)
2. SCHWARZE Messspitze → PE-Kontakt (Mitte, Schutzleiter)
3. MESSEN-Taste drücken (oder automatisch bei 500V-Stellung)
4. Wert ablesen und notieren
```

**Messpunkt 2: N/PE (Neutralleiter gegen Schutzleiter)**

```
1. ROTE Messspitze → N-Kontakt im Stecker (rechts bei Schuko)
2. SCHWARZE Messspitze → PE-Kontakt (Mitte)
3. Messen und notieren
```

### **Schutzklasse II (Doppelisolierung, ohne Schutzleiter):**

**Messpunkt: L+N gegen berührbare Metallteile**

```
1. ROTE Messspitze → L-Kontakt im Stecker
2. SCHWARZE Messspitze → berührbare Metallteile am Gerät
   (Gehäuse, Schrauben, Griffe, etc.)
3. Messen und notieren
```

**Alternative:** L und N im Stecker überbrücken, dann gegen Gehäuse messen

### **Schutzklasse III (Schutzkleinspannung, z.B. 12V/24V Geräte):**

```
1. Messung zwischen Eingangs- und Ausgangsseite
2. Oder gemäß Herstellerangaben
```

---

## 📊 MESSWERTE INTERPRETIEREN

### **Grenzwerte für Repair-Café (UNI-T UT-501, 500V):**

| Schutzklasse | Mindestwert | Bewertung |
|--------------|-------------|-----------|
| **SK I** (ohne Heizung) | ≥ 1.0 MΩ | ✅ OK |
| **SK I** (mit Heizung) | ≥ 0.3 MΩ | ✅ OK |
| **SK II** (Doppelisolierung) | ≥ 2.0 MΩ | ✅ OK |
| **SK III** (Schutzkleinspannung) | ≥ 0.25 MΩ | ✅ OK |

### **Bewertung:**

```
≥ Grenzwert     →  ✅ BESTANDEN (Isolation in Ordnung)
< Grenzwert     →  ❌ NICHT BESTANDEN (Isolation defekt)
"OL" (Over Limit) → ✅ SEHR GUT (Isolation > 2000 MΩ)
0.00 MΩ         →  ❌ KURZSCHLUSS (sofort aussondern!)
```

---

## 🛠️ PRAKTISCHE BEISPIELE

### **Beispiel 1: Toaster (SK I, mit Heizung)**

```
Gerät: Toaster, 1000W
Schutzklasse: I (Schukostecker)
Heizleistung: 1.0 kW

Messung:
  L/PE: 150 MΩ  ✅
  N/PE: 145 MΩ  ✅

Grenzwert: ≥ 0.3 MΩ (mit Heizung)
Urteil: BESTANDEN ✅
```

### **Beispiel 2: Bohrmaschine (SK I, Motor)**

```
Gerät: Handbohrmaschine, 500W
Schutzklasse: I (Schukostecker)

Messung:
  L/PE: 0.8 MΩ  ✅
  N/PE: 0.7 MΩ  ✅

Grenzwert: ≥ 1.0 MΩ (ohne Heizung)
Urteil: BESTANDEN ✅ (knapp, aber OK)
```

### **Beispiel 3: Haartrockner (SK II)**

```
Gerät: Haartrockner, 1800W
Schutzklasse: II (Doppelisolierung, kein Schutzleiter)

Messung:
  L+N gegen Gehäuse: 250 MΩ  ✅

Grenzwert: ≥ 2.0 MΩ
Urteil: BESTANDEN ✅
```

### **Beispiel 4: Defektes Netzteil (SK I)**

```
Gerät: Laptop-Netzteil
Schutzklasse: I (Schukostecker)

Messung:
  L/PE: 0.05 MΩ  ❌
  N/PE: 0.04 MΩ  ❌

Grenzwert: ≥ 1.0 MΩ
Urteil: NICHT BESTANDEN ❌
→ Isolation defekt, von Reparatur abraten!
```

---

## ⚠️ HÄUFIGE FEHLER

### **Falsche Messwerte durch:**

```
❌ Feuchte Anschlüsse → Trocknen, neu messen
❌ Schmutzige Kontakte → Reinigen, neu messen
❌ Kondensatoren noch geladen → Entladen, neu messen
❌ Falsche Schutzklasse → Geräte-Typenschild prüfen
❌ Messleitungen vertauscht → Korrekt anschließen
❌ Gerät nicht ausgeschaltet → Alle Schalter EIN stellen
```

### **Typische Probleme:**

| Symptom | Ursache | Lösung |
|---------|---------|--------|
| **0.00 MΩ** | Kurzschluss | Gerät nicht sicher! |
| **"OL"** | Sehr gute Isolation | ✅ Bestanden |
| **Wert steigt langsam** | Kondensator lädt | Warten bis stabil |
| **Wert schwankt** | Feuchte/Wackelkontakt | Trocknen, festhalten |

---

## 📝 DOKUMENTATION IM REPAIR-CAFÉ

### **Im Laufzettel-System:**

1. **Isolationswiderstand eingeben** (z.B. `150` für 150 MΩ)
2. **Einheit:** MΩ (Megaohm)
3. **System bewertet automatisch:**
   - ≥ Grenzwert → ✅ BESTANDEN
   - < Grenzwert → ❌ NICHT BESTANDEN

### **Protokoll zeigt:**

```
⚡ Isolationsprüfung mit UNI-T UT-501 (nicht VDE-konform)

Messgröße                          Grenzwert    Messwert    Bewertung
─────────────────────────────────────────────────────────────────────
Isolationswiderstand (UNI-T UT-501, 500V)   ≥ 1.0 MΩ    150 MΩ      ✓
```

---

## 🔋 WARTUNG

### **Batteriewechsel:**
```
→ Display zeigt "🔋" oder wird dunkel
→ 6 × AA Batterien wechseln
→ Fach auf der Rückseite öffnen
```

### **Aufbewahrung:**
```
✅ Trocken lagern (nicht im feuchten Keller)
✅ Messleitungen ordentlich aufwickeln
✅ Vor Staub schützen (Tasche verwenden)
```

### **Regelmäßige Prüfung:**
```
□ Sichtprüfung der Messleitungen (Brüche?)
□ Funktionstest an bekanntem Widerstand
□ Gehäuse auf Beschädigung prüfen
```

---

## 📞 HILFE IM REPAIR-CAFÉ

**Bei Unsicherheit:**

1. **Erfahrenen Helfer fragen**
2. **Geräte-Typenschild prüfen** (Schutzklasse!)
3. **Im Reparatur-Tagebuch nachsehen** (ähnliche Fälle)
4. **Lieber zu vorsichtig sein als zu riskant**

---

## 🚫 HAFTUNGSAUSSCHLUSS

```
⚠️ Diese Anleitung ersetzt KEINE VDE-gerechte Prüfung!

Die Isolationsprüfung mit UNI-T UT-501 ist:
  • NICHT VDE-konform
  • NICHT nach DGUV V3 zertifiziert
  • NUR für interne Repair-Café Zwecke

Rechtliche Grundlage: Reparatur- und Haftungsvereinbarung
(unterschrieben bei Ticket-Erstellung)

Bei gewerblichen Geräten oder Unsicherheit:
  → Fachbetrieb empfehlen
  → Nicht reparieren
```

---

**Version:** 2026-09-05  
**Erstellt für:** Repair-Café berlin Creators  
**Gerät:** UNI-T UT-501 Isolationswiderstand-Tester
