# UNI-T UT-501 Isolationsprüfgerät — Bedienanleitung

**⚠️ WICHTIG: NUR für Leitungen/Kabel — NICHT für Geräte!**

**Einsatz im Repair-Café** — Seit 2026-09-05

---

## 🚨 KRITISCHER WARNHINWEIS

```
⚠️  ACHTUNG: UT-501 ist NUR für lose Leitungen/Kabel!

❌ NICHT für fertige Geräte verwenden!
   - Weder Schutzklasse I (230V-Geräte)
   - Weder Schutzklasse II (schutzisolierte Geräte)
   - Weder Schutzklasse III (Kleinspannung, 5V-Geräte)

✅ NUR für isolierte Leitungen/Kabel:
   - Isolationswiderstand zwischen Adern messen
   - NICHT im Repair-Café für Geräte-Reparaturen!

✅ Für ALLE Geräte-Reparaturen:
   - NUR Multimeter verwenden (Durchgang, Spannung)
   - Besichtigung + Funktionsprüfung
   - KEINE Isolationsprüfung!
```

**Hintergrund:** Der UT-501 mit 500V DC ist ausschließlich für die Isolationsprüfung von elektrischen Leitungen und Kabeln konzipiert. Die Prüfung an fertigen Geräten kann:
- ❌ Elektronikbauteile zerstören (500V!)
- ❌ Falsche Messwerte liefern (Geräte-Parallelschaltungen)
- ❌ Sicherheitsrisiken schaffen (Kondensatoren, Varistoren)

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

## 🔧 MESSDURCHFÜHRUNG

### **⚠️ NUR für Leitungen/Kabel!**

**WICHTIG:** Diese Anleitung beschreibt die Messung an **isolierten Leitungen**, NICHT an fertigen Geräten!

```
✅ RICHTIG: Isolationswiderstand zwischen zwei Adern eines Kabels
❌ FALSCH: Isolationswiderstand an einem fertigen Gerät (Toaster, Föhn, etc.)
```

### **Messung an einem Kabel (2-adrig):**

```
1. BEIDE Enden des Kabels freilegen (nicht verbunden!)
2. ROTE Messspitze → Ader 1 (ein Ende)
3. SCHWARZE Messspitze → Ader 2 (gleiches Ende)
4. MESSEN-Taste drücken
5. Wert ablesen (sollte > 100 MΩ sein für gute Isolierung)
```

### **Messung an einem Kabel (mehradrig):**

```
Jede Ader gegen jede andere Ader prüfen:
- Ader 1 gegen Ader 2
- Ader 1 gegen Ader 3
- Ader 2 gegen Ader 3
- etc.

Alle Werte sollten > 100 MΩ sein.
```

---

### **❌ NICHT für Geräte-Reparaturen!**

**Für ALLE Geräte im Repair-Café gilt:**

```
1. Besichtigung (Gehäuse, Kabel, Stecker)
2. Multimeter-Prüfung (Durchgang, Spannung)
3. Funktionsprüfung (nach Reparatur)

KEINE Isolationsprüfung mit UT-501!
```

**Multimeter verwenden für:**
- ✅ Durchgangsprüfung (Kabel defekt?)
- ✅ Spannung messen (Dynamo: 5-12V DC)
- ✅ Widerstand messen (LED, Schalter)

**Alternative:** L und N im Stecker überbrücken, dann gegen Gehäuse messen

---

## ❌ NICHT FÜR GERÄTE!

**Diese Anleitung war ursprünglich für Geräte-Reparaturen gedacht — das ist FALSCH!**

### **RICHTIGER WORKFLOW für Geräte im Repair-Café:**

```
1. Besichtigung (Gehäuse, Kabel, Stecker, Schalter)
2. Multimeter-Prüfung:
   - Durchgang (Kabel OK?)
   - Spannung (Dynamo: 5-12V DC)
   - Widerstand (LED, Schalter)
3. Reparatur durchführen
4. Funktionsprüfung (gerät funktioniert?)

❌ KEINE Isolationsprüfung mit UT-501!
```

### **Wann UT-501 verwenden?**

```
✅ NUR für isolierte Leitungen/Kabel:
   - Selbst gebaute Verlängerungskabel
   - Verlegte Leitungen (Isolationszustand)
   - Kabelbäume (Isolation zwischen Adern)

❌ NICHT für fertige Geräte:
   - Toaster, Föhn, Kaffeemaschine
   - Bohrmaschine, Haartrockner
   - Netzteile, Lampen
   - Dynamo-Taschenlampen (5V!)
```

---

## 📊 GRENZWERTE (NUR für Leitungen/Kabel!)

### **Für isolierte Leitungen:**

| Kabeltyp | Mindest-Isolationswiderstand | Bewertung |
|----------|------------------------------|-----------|
| **Neue Leitung** | > 1000 MΩ | ✅ Sehr gut |
| **Gebrauchte Leitung** | > 100 MΩ | ✅ Gut |
| **Alte Leitung** | 10–100 MΩ | ⚠️ Prüfen (noch OK) |
| **Defekte Leitung** | < 10 MΩ | ❌ Isolierung defekt! |

### **❌ KEINE Grenzwerte für Geräte!**

**Für Geräte-Reparaturen gibt es KEINE Grenzwerte weil:**
- ❌ **KEINE Isolationsprüfung** an Geräten!
- ✅ **NUR Multimeter** (Durchgang, Spannung)
- ✅ **Besichtigung + Funktionsprüfung**

---

## 🛠️ PRAKTISCHE BEISPIELE

### **✅ RICHTIG: Kabel-Prüfung**

**Beispiel 1: Selbst gebautes Verlängerungskabel**

```
Kabel: H05VV-F 3G1.5 (selbst konfektioniert)
Länge: 5m

Messung (je Ader-Kombination):
  L1 gegen L2:  > 1000 MΩ  ✅
  L1 gegen PE:  > 1000 MΩ  ✅
  L2 gegen PE:  > 1000 MΩ  ✅

Grenzwert: > 100 MΩ (gebrauchte Leitung)
Urteil: BESTANDEN ✅ (sehr gute Isolierung)
```

### **❌ FALSCH: Geräte-Prüfung (NICHT machen!)**

**Beispiel 2: Toaster (falsch geprüft!)**

```
Gerät: Toaster, 1000W
Schutzklasse: I (Schukostecker)

❌ FALSCH: UT-501 am Gerät verwenden!
   → 500V kann Heizwendel-Elektronik zerstören
   → Falsche Werte durch Parallelschaltungen

✅ RICHTIG: Multimeter verwenden
   - Durchgang: Heizwendel OK?
   - Besichtigung: Kabel, Stecker, Gehäuse
   - Funktionsprüfung: Wird er heiß?
```

---

## ⚠️ HÄUFIGE FEHLER

### **Falsche Messwerte durch:**

```
❌ Feuchte Anschlüsse → Trocknen, neu messen
❌ Schmutzige Kontakte → Reinigen, neu messen
❌ Kondensatoren noch geladen → Entladen, neu messen
❌ Falsche Anwendung → UT-501 NUR für Kabel, NICHT für Geräte!
❌ Messleitungen vertauscht → Korrekt anschließen
```

### **Typische Probleme:**

| Symptom | Ursache | Lösung |
|---------|---------|--------|
| **0.00 MΩ** | Kurzschluss | Leitung defekt! |
| **"OL"** | Sehr gute Isolation | ✅ Bestanden |
| **Wert steigt langsam** | Kondensator lädt | Warten bis stabil |
| **Wert schwankt** | Feuchte/Wackelkontakt | Trocknen, festhalten |

---

## 📝 DOKUMENTATION IM REPAIR-CAFÉ

### **Wann dokumentieren?**

```
✅ NUR wenn: Isolationsprüfung an Kabeln durchgeführt
   - Selbst konfektionierte Kabel
   - Verlegte Leitungen geprüft

❌ NICHT wenn: Geräte-Reparatur
   - Normale Reparatur (Besichtigung + Funktion)
   - Multimeter-Prüfung (Durchgang, Spannung)
```

### **Multimeter-Prüfung dokumentieren:**

```
Im Laufzettel:
□ Besichtigung: OK
□ Durchgang: Kabel OK
□ Spannung: 12V (Dynamo)
□ Funktion: LED leuchtet

✅ FERTIG! (KEINE Isolationsprüfung!)
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
