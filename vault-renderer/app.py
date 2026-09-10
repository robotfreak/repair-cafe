#!/usr/bin/env python3
"""
Repair-Café Vault Renderer
Rendert den Obsidian Vault (20-Bereiche/Repair-Cafe) als Web-Interface
"""

from flask import Flask, render_template, send_from_directory, abort, url_for
import os
import markdown
import re


def convert_obsidian_links(text, base_path=''):
    """Konvertiert [[Link]] zu HTML-Links mit korrektem Pfad"""
    def replace_link(match):
        link_text = match.group(1)
        # Alias-Text extrahieren falls vorhanden [[Link|Text]]
        display_text = link_text
        if '|' in link_text:
            link_text, display_text = link_text.split('|', 1)
        
        # Ordner-Pfad extrahieren
        folder = ''
        if '/' in link_text:
            parts = link_text.rsplit('/', 1)
            folder = parts[0] + '/'
            link_text = parts[1]
        
        # Dateiendung hinzufügen wenn nötig
        if not link_text.endswith('.md'):
            link_text += '.md'
        
        # URL zusammenbauen
        link_url = f'/vault/{base_path}{folder}{link_text}'
        return f'<a href="{link_url}">{display_text}</a>'
    
    # [[Link Text]] Pattern
    text = re.sub(r'\[\[([^\]]+)\]\]', replace_link, text)
    return text


app = Flask(__name__)

# Konfiguration
VAULT_PATH = '/home/pi/repair-cafe/vault/20-Bereiche/Repair-Cafe'


@app.route('/')
def index():
    """Startseite mit Vault-Übersicht"""
    uebersicht_path = os.path.join(VAULT_PATH, '00-Uebersicht.md')
    if os.path.exists(uebersicht_path):
        with open(uebersicht_path, 'r') as f:
            content = f.read()
        html = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        html = convert_obsidian_links(html)
        return render_template('page.html', title='Repair-Café Verwaltung', content=html)
    else:
        return render_template('index.html', vault_path=VAULT_PATH)


@app.route('/vault/<path:filename>')
def vault_file(filename):
    """Vault Markdown-Dateien rendern oder Ordner auflisten"""
    filepath = os.path.join(VAULT_PATH, filename)
    
    if not filepath.startswith(VAULT_PATH):
        abort(403)
    
    # Wenn es ein Ordner ist, zeige die .md Dateien darin
    if os.path.isdir(filepath):
        files = []
        for f in sorted(os.listdir(filepath)):
            if f.endswith('.md'):
                files.append(f)
        return render_template('folder.html', folder=filename, files=files)
    
    if not os.path.exists(filepath):
        abort(404)
    
    if filename.endswith('.md'):
        with open(filepath, 'r') as f:
            content = f.read()
        html = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        folder_path = os.path.dirname(filename) + '/' if os.path.dirname(filename) else ''
        html = convert_obsidian_links(html, folder_path)
        return render_template('page.html', title=filename.replace('.md', ''), content=html)
    else:
        return send_from_directory(VAULT_PATH, filename)


@app.route('/<path:filename>')
def static_file(filename):
    """Statische Dateien ausliefern"""
    return send_from_directory('static', filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8054, debug=False)
