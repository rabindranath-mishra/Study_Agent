#!/usr/bin/env python3
"""Create a new markdown note in an Obsidian vault with optional YAML frontmatter.

Usage (Windows PowerShell):
  # Method 1: Via stdin (recommended for large content, run from vault root)
  $content | .\\"00 - System"\\.agent\\venv\\Scripts\\python.exe ".\\00 - System\\.agent\\tools\\create_note.py" . "Note Title" --stdin

  # Method 2: Via argument (for small content, run from vault root)
  .\\"00 - System"\\.agent\\venv\\Scripts\\python.exe ".\\00 - System\\.agent\\tools\\create_note.py" . "Note Title" "# Content..."

Prints JSON: {"path": "..."}
"""
import sys
import argparse
from pathlib import Path
import datetime
import json
import re

def slugify(title: str) -> str:
    s = title.strip().lower()
    s = re.sub(r'[^a-z0-9\\-\\_ ]', '', s)
    s = s.replace(' ', '-')
    return s

def normalise_tags(content: str) -> str:
    """Convert inline YAML tag arrays to Obsidian block-list style.

    Transforms:  tags: [english, poetry, class-11]
    Into:        tags:
                   - english
                   - poetry
                   - class-11

    Only operates inside the first frontmatter block (between the opening
    and closing '---' delimiters) so body content is never touched.
    """
    fm_match = re.match(r'^(---\n)(.*?\n)(---\n)', content, re.DOTALL)
    if not fm_match:
        return content

    prefix, fm_body, suffix = fm_match.group(1), fm_match.group(2), fm_match.group(3)
    rest = content[fm_match.end():]

    def _expand_tags(m):
        raw = m.group(1).strip()
        # Strip surrounding brackets if present
        raw = raw.strip('[]')
        tags = [t.strip().strip('"').strip("'") for t in raw.split(',') if t.strip()]
        lines = '\n'.join(f'  - {t}' for t in tags)
        return f'tags:\n{lines}\n'

    fm_body = re.sub(r'tags:\s*\[([^\]]+)\]\s*\n', _expand_tags, fm_body)
    return prefix + fm_body + suffix + rest

def create_note(vault_dir: str, title: str, content: str, filename_template: str = "{title}.md", folder: str = ""):
    vault = Path(vault_dir).expanduser().resolve()
    if not vault.exists():
        raise SystemExit(f"Vault path does not exist: {vault}")

    # Strip UTF-8 BOM that PowerShell may prepend when piping strings
    content = content.lstrip('\ufeff')

    date = datetime.datetime.now().strftime('%Y-%m-%d')
    slug = slugify(title)
    filename = filename_template.format(date=date, title=title, slug=slug)
    
    # Add folder support
    if folder:
        target_dir = vault / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / filename
    else:
        path = vault / filename
    counter = 1
    while path.exists():
        path = vault / f"{filename.replace('.md', '')}-{counter}.md"
        counter += 1

    if not content.strip().startswith('---'):
        frontmatter = f"""---
title: "{title}"
date: {date}
---

"""
        content = frontmatter + content

    # Normalise tags to Obsidian block-list style
    content = normalise_tags(content)

    path.write_text(content, encoding='utf-8')
    return str(path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('vault', help='Path to Obsidian vault')
    parser.add_argument('title', help='Title of the note')
    parser.add_argument('content', nargs='?', default=None, help='Markdown content for the note (or use --stdin)')
    parser.add_argument('--stdin', action='store_true', help='Read content from stdin (recommended for large content)')
    parser.add_argument('--filename-template', default='{title}.md', help='Filename template (format fields: date, title, slug)')
    parser.add_argument('--folder', default='', help='Subfolder within vault (e.g., "03 - Research")')
    args = parser.parse_args()

    # Get content from stdin if flag set, otherwise use positional argument
    if args.stdin:
        import io
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
        content = sys.stdin.read()
    elif args.content:
        content = args.content
    else:
        sys.stdout.buffer.write(json.dumps({"success": False, "error": "Content required via argument or --stdin"}).encode('utf-8') + b'\n')
        sys.exit(1)

    try:
        out_path = create_note(args.vault, args.title, content, args.filename_template, args.folder)
        sys.stdout.buffer.write(json.dumps({"success": True, "path": out_path}).encode('utf-8') + b'\n')
    except Exception as e:
        sys.stdout.buffer.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8') + b'\n')
        sys.exit(1)
