# 🚀 VAULT REPO ERSTELLEN — Anleitung

## SCHRITT 1: GitHub Repo erstellen

Gehe zu: **https://github.com/new**

**Einstellungen:**
- **Repository name:** `vault`
- **Beschreibung:** "Obsidian Vault — Single Source of Truth"
- **Privat:** ✅ Ja (oder öffentlich wenn du willst)
- **❌ NICHT initialisieren** (kein README, kein .gitignore!)
- **"Create repository"** klicken

---

## SCHRITT 2: Vault hochladen

Auf deinem Pi:

```bash
cd /tmp/vault-export

# GitHub Repo URL (nachdem du es erstellt hast)
git remote set-url origin git@github.com:robotfreak/vault.git

# Oder wenn noch nicht gesetzt
git remote add origin git@github.com:robotfreak/vault.git

# Hochladen
git push -u origin main
```

---

## SCHRITT 3: ki-os aktualisieren

```bash
cd ~/ki-os

# Altes vault Submodule entfernen (wenn vorhanden)
git submodule deinit -f vault 2>/dev/null || true
rm -rf .git/modules/vault 2>/dev/null || true
git rm -f vault 2>/dev/null || true

# Neues vault Submodule hinzufügen
git submodule add git@github.com:robotfreak/vault.git vault

# Commit
git add .gitmodules vault
git commit -m "feat: vault als eigenes Submodule (github.com:robotfreak/vault)"
git push
```

---

## SCHRITT 4: repair-cafe aktualisieren

```bash
cd ~/repair-cafe

# Altes ki-os Submodule entfernen
git submodule deinit -f ki-os
rm -rf .git/modules/ki-os
git rm -f ki-os

# Neues vault Submodule hinzufügen
git submodule add git@github.com:robotfreak/vault.git vault

# docs_viewer.py Pfad anpassen
# In app/docs_viewer.py:
#   VAULT_PATH = Path(__file__).parent.parent / 'vault'
#   (statt 'ki-os' / 'vault')

# Commit
git add .gitmodules vault app/docs_viewer.py
git commit -m "feat: vault als eigenes Submodule (github.com:robotfreak/vault)"
git push
```

---

## SCHRITT 5: Testen

```bash
# Vault öffnen
cd ~/repair-cafe/vault
ls -la

# Sollte zeigen:
# 00-Inbox/
# 10-Projekte/
# 40-Ressourcen/
# ...
```

---

## ✅ FERTIG!

**Struktur jetzt:**

```
GitHub:
├── robotfreak/ki-os
│   └── vault/ → github.com:robotfreak/vault.git
├── robotfreak/repair-cafe
│   └── vault/ → github.com:robotfreak/vault.git
└── robotfreak/vault  ← Eigenes Repo!

Lokal:
~/ki-os/vault/      → Symlink zu vault Repo
~/repair-cafe/vault/ → Symlink zu vault Repo
```

---

**Bei Fragen:** Einfach melden! 🔧
