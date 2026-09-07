"""Markdown-Renderer für Vault-Dokumentation."""
import markdown
from flask import Blueprint, render_template, abort, url_for
from pathlib import Path
import os

bp = Blueprint('docs', __name__, url_prefix='/docs')

# Vault-Pfad im Submodule
VAULT_PATH = Path(__file__).parent.parent / 'vault'

def get_vault_structure():
    """Gibt die Vault-Ordnerstruktur als Dict zurück."""
    structure = {}
    
    # NUR Repair-Café Bereich anzeigen!
    folder_order = [
        '20-Bereiche/Repair-Cafe',  # ← NUR Repair-Café!
    ]
    
    for folder_name in folder_order:
        folder_path = VAULT_PATH / folder_name
        if folder_path.exists():
            files = []
            for md_file in folder_path.glob('*.md'):
                # Titel aus Filename oder Frontmatter
                title = md_file.stem.replace('-', ' ').replace('_', ' ')
                files.append({
                    'name': md_file.name,
                    'title': title,
                    'path': f'{folder_name}/{md_file.name}',
                    'full_path': str(md_file),
                })
            
            structure[folder_name] = files
    
    return structure


@bp.route('/')
def docs_index():
    """Zeigt alle Vault-Dokumente als durchsuchbare Liste."""
    structure = get_vault_structure()
    return render_template('docs/index.html', structure=structure)


@bp.route('/<path:filename>')
def show_doc(filename):
    """Rendert ein Markdown-Dokument als HTML."""
    md_file = VAULT_PATH / filename
    
    if not md_file.exists():
        # Versuch mit .md Extension
        md_file = VAULT_PATH / f"{filename}.md"
        if not md_file.exists():
            abort(404)
    
    # Markdown lesen und rendern
    content = md_file.read_text(encoding='utf-8')
    
    # Frontmatter extrahieren (--- ... --- am Anfang)
    frontmatter = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            content = parts[2].strip()
            # Einfaches Frontmatter-Parsing
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
    
    # Markdown zu HTML konvertieren
    html_content = markdown.markdown(
        content,
        extensions=[
            'extra',           # Tabellen, Definitionen, etc.
            'toc',             # Inhaltsverzeichnis
            'fenced_code',     # Code-Blöcke
            'tables',
        ]
    )
    
    # Titel aus Frontmatter oder Filename
    title = frontmatter.get('title', md_file.stem.replace('-', ' ').replace('_', ' '))
    
    return render_template('docs/document.html', 
                         content=html_content,
                         title=title,
                         filename=filename)
