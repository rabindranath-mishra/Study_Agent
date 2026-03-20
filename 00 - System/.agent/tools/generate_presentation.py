#!/usr/bin/env python3
"""
generate_presentation.py — Generate self-contained offline HTML presentations (standalone deck, no framework).

Input modes:
  1. Markdown mode: parse a .md file or stdin markdown into slides
  2. HTML passthrough mode: stdin/file contains <div class="slide"> HTML bodies directly

All assets (CSS, images) are inlined. Works fully offline.

Usage:
  python generate_presentation.py --source "path/to/note.md" --title "My Talk"
  python generate_presentation.py --source "path/to/note.md" --output-dir "07 - Writing/Presentations"

Output JSON:
  {"success": true, "path": "...", "slide_count": 5, "file_size_kb": 210}
"""

import sys
import os
import re
import json
import base64
import argparse
import html as html_module
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
from paths import VAULT_ROOT as _vault_root_str
TOOLS_DIR          = Path(__file__).parent
VAULT_ROOT         = Path(_vault_root_str)
OUTPUT_DIR_NAME    = "07 - Writing/presentations"

# ---------------------------------------------------------------------------
# Philips brand assets (base64-embedded, vault-contained)
# ---------------------------------------------------------------------------
_PHL_LOGO_WHITE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAuwAAACJCAMAAABAWJ0OAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAKyUExURQAAAP///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////xDJ/bcAAADldFJOUwABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGxwdHh8gISIjJCUnKCkqKywuLzAxMjM0NTY3ODk6Ozw9Pj9AQUJDREVGR0lKS0xNTlBRUlNUVVZXWVtcXV5fYGFiY2RmZ2psbW5vcHFzdHV2d3l6e3x9fn+AgoOEhoeIiYuMjo+Q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"  # 748x137 white logo — title slides (dark bg)
_PHL_LOGO_BLUE_B64  = "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"   # 277x51 blue logo  — footer on white bg

_PHL_FOOTER_CSS = """
/* phl brand elements — now live inside .s-footer */
.phl-footer-copy { font-size: 10px; color: #57606a; font-family: 'Segoe UI', system-ui, sans-serif; letter-spacing: 0.01em; white-space:nowrap; }
.phl-footer-logo { height: 16px; width: auto; opacity: 0.85; }
"""


# ---------------------------------------------------------------------------
# Slide model
# ---------------------------------------------------------------------------

@dataclass
class Slide:
    type: str           # cover | section | content | quote | table | image
    title: str = ""
    subtitle: str = ""
    body_html: str = ""
    meta: dict = field(default_factory=dict)

# ---------------------------------------------------------------------------
# Component CSS — custom standalone slide deck (no Reveal.js)
# ---------------------------------------------------------------------------

COMPONENT_CSS = """
/* ── Reset ── */
*{margin:0;padding:0;box-sizing:border-box;}
/* ── Variables ── */
:root{
  --blue:#0B5ED7;--navy:#00126E;--green:#16a34a;--purple:#7c3aed;
  --teal:#0891b2;--orange:#d97706;--red:#dc2626;
  --bg:#ffffff;--surface:#f6f8fa;--surface2:#eaeef2;
  --border:#d0d7de;--text:#24292f;--muted:#57606a;
  --font:'Segoe UI',system-ui,-apple-system,sans-serif;
}
html,body{width:100%;height:100%;overflow:hidden;background:var(--bg);font-family:var(--font);color:var(--text);}
/* ── Deck ── */
#deck{width:100vw;height:100vh;position:relative;overflow:hidden;}
/* ── Slide: mandatory 4-zone grid (header | body[left/right] | footer) ── */
.slide{
  position:absolute;inset:0;width:100%;height:100%;
  display:grid;grid-template-rows:auto 1fr auto;
  opacity:0;pointer-events:none;font-size:16px;
  transform:translateX(80px);
  transition:opacity .38s ease,transform .38s ease;
  overflow:hidden;background:var(--bg);
}
.slide.active{opacity:1;pointer-events:auto;transform:translateX(0);}
.slide.exit{opacity:0;transform:translateX(-80px);}
/* ── Zone 1: Header (full width, top) ── */
.s-header{
  padding:16px 52px 12px;border-bottom:2px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;gap:20px;
  background:var(--bg);flex-shrink:0;
}
/* RULE: s-header-title must be the main point only — max ~6 words, no description.
   Long text is intentionally clipped to enforce discipline. */
.s-header-title{font-size:4.6em;font-weight:700;color:var(--navy);flex:1;line-height:1.3;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.s-header-label{
  font-size:.72em;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
  color:var(--blue);padding:4px 12px;border:1px solid var(--blue);
  border-radius:20px;white-space:nowrap;flex-shrink:0;
}
/* ── Zone 2: Body — strict 50/50 left/right split ── */
.s-body{display:flex;flex-direction:row;min-height:0;overflow:hidden;}
/* ── Zone 2a: Left half — bullets (max 5) ── */
.s-left{
  flex:0 0 50%;width:50%;
  border-right:none;
  padding:28px 40px;display:flex;flex-direction:column;overflow:hidden;min-height:0;
}
/* ── Zone 2b: Right half — diagram/visual ── */
.s-right{
  flex:0 0 50%;width:50%;
  padding:20px 32px;display:flex;align-items:center;justify-content:center;
  overflow:hidden;min-height:0;
}
.s-right>*{max-width:100%;max-height:100%;}
.s-right svg{width:100%;height:100%;max-height:100%;}
/* ── Zone 3: Footer (full width, bottom) ── */
.s-footer{
  padding:7px 52px;border-top:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  font-size:.72em;color:var(--muted);flex-shrink:0;background:var(--surface);
}
.s-footer-title{font-style:italic;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;margin:0 16px;}
.s-footer-brand{display:flex;align-items:center;gap:8px;flex-shrink:0;}
.s-footer-nav{display:flex;align-items:center;gap:6px;flex-shrink:0;}
.nav-ctr{font-size:1em;color:var(--muted);min-width:44px;text-align:center;}
/* ── Cover / Title slide (overrides grid with full-bleed flex) ── */
.slide.title-slide{
  display:flex !important;flex-direction:column;
  justify-content:center;align-items:flex-start;
  padding:80px;background-color:var(--navy);
  background-size:cover;background-position:center;
  print-color-adjust:exact;-webkit-print-color-adjust:exact;
}
.cover-content{max-width:72%;}
.cover-title{font-size:5.2em !important;font-weight:800 !important;color:#ffffff !important;
  line-height:1.15 !important;text-align:left !important;margin:0 0 14px 0 !important;
  text-shadow:0 2px 6px rgba(0,0,0,0.5) !important;}
.cover-subtitle{font-size:2.1em;color:rgba(255,255,255,0.85) !important;
  text-align:left !important;text-shadow:0 1px 3px rgba(0,0,0,0.5);}
/* ── Backward-compat aliases (old s-head / col names still render) ── */
.s-head{padding:16px 52px 12px;border-bottom:2px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:20px;background:var(--bg);}
.s-head-title{font-size:1.15em;font-weight:700;color:var(--navy);flex:1;line-height:1.3;}
.s-head-label{font-size:.72em;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--blue);padding:4px 12px;border:1px solid var(--blue);border-radius:20px;white-space:nowrap;}
.col{flex:1;display:flex;flex-direction:column;overflow:hidden;}
.col-wide{flex:0 0 50%;width:50%;padding:28px 40px;}
.col-narrow{flex:0 0 50%;width:50%;padding:20px 32px;display:flex;align-items:center;justify-content:center;}
/* ── Bullets (left half — max 5, evenly distributed, MUST NOT overflow) ── */
.bullets{list-style:none;display:flex;flex-direction:column;flex:1;min-height:0;}
.bullets li{display:flex;gap:10px;align-items:flex-start;font-size:1.76em;line-height:1.45;padding:5px 0;border-bottom:1px solid var(--border);flex:1;min-height:0;overflow:hidden;}
.bullets li:last-child{border-bottom:none;}
.ico{flex-shrink:0;width:26px;height:26px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:.78em;margin-top:1px;}
.ico.g{background:rgba(22,163,74,.14);color:var(--green);}
.ico.b{background:rgba(11,94,215,.14);color:var(--blue);}
.ico.o{background:rgba(217,119,6,.14);color:var(--orange);}
.ico.r{background:rgba(220,38,38,.14);color:var(--red);}
.ico.t{background:rgba(8,145,178,.14);color:var(--teal);}
.ico.p{background:rgba(124,58,237,.14);color:var(--purple);}
.bt strong{color:var(--navy);font-weight:600;}
.bt .d{display:block;font-size:.84em;color:var(--muted);margin-top:2px;}
/* ── Stat cards ── */
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 14px;text-align:center;}
.stat-card .v{font-size:1.8em;font-weight:700;color:var(--blue);line-height:1;}
.stat-card .u{font-size:.72em;color:var(--muted);margin-top:3px;}
.stat-card .l{font-size:.76em;color:var(--muted);margin-top:7px;line-height:1.4;}
/* ── Table ── */
.spec-t{border-collapse:collapse;width:100%;font-size:.87em;}
.spec-t td{padding:7px 11px;border-bottom:1px solid var(--border);}
.spec-t tr:last-child td{border-bottom:none;}
.spec-t td:first-child{color:var(--muted);width:42%;}
.spec-t td:last-child{color:var(--text);font-weight:600;}
/* ── Callout ── */
.callout{background:rgba(11,94,215,.07);border:1px solid rgba(11,94,215,.22);border-left:3px solid var(--blue);border-radius:8px;padding:10px 14px;font-size:.86em;line-height:1.5;}
.callout strong{color:var(--blue);}
.callout.warn{background:rgba(217,119,6,.07);border-color:rgba(217,119,6,.3);border-left-color:var(--orange);}
.callout.warn strong{color:var(--orange);}
.callout.success{background:rgba(22,163,74,.07);border-color:rgba(22,163,74,.3);border-left-color:var(--green);}
.callout.success strong{color:var(--green);}
/* ── Timeline ── */
.timeline{display:flex;flex-direction:column;gap:10px;}
.tl-item{display:flex;gap:10px;align-items:flex-start;}
.tl-dot{width:10px;height:10px;border-radius:50%;background:var(--blue);flex-shrink:0;margin-top:4px;}
.tl-body{font-size:.86em;line-height:1.4;}
/* ── Chips ── */
.chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px;}
.chip{font-size:.72em;font-weight:600;padding:4px 11px;border-radius:20px;letter-spacing:.05em;}
.chip.g{background:rgba(22,163,74,.1);color:var(--green);border:1px solid rgba(22,163,74,.28);}
.chip.b{background:rgba(11,94,215,.1);color:var(--blue);border:1px solid rgba(11,94,215,.28);}
.chip.p{background:rgba(124,58,237,.1);color:var(--purple);border:1px solid rgba(124,58,237,.28);}
.chip.o{background:rgba(217,119,6,.1);color:var(--orange);border:1px solid rgba(217,119,6,.28);}
.chip.t{background:rgba(8,145,178,.1);color:var(--teal);border:1px solid rgba(8,145,178,.28);}
/* ── Cover-slide chip override: dark background requires white chip text ── */
.slide.title-slide .chip{background:rgba(255,255,255,0.15) !important;color:#ffffff !important;border:1px solid rgba(255,255,255,0.35) !important;}
/* ── Diagram wrapper (right half) ── */
.dw{flex:1;display:flex;align-items:center;justify-content:center;min-height:0;}
.dw svg,.slide-image,.inline-image{max-width:100%;max-height:100%;object-fit:contain;}
/* ── Nav ── */
.nb{background:var(--surface);border:1px solid var(--border);color:var(--text);width:28px;height:28px;border-radius:6px;cursor:pointer;font-size:.95em;display:flex;align-items:center;justify-content:center;transition:background .2s,border-color .2s;}
.nb:hover{background:var(--surface2);border-color:var(--blue);}
/* ── Progress bar ── */
#pb{position:fixed;bottom:0;left:0;height:3px;background:var(--blue);transition:width .35s;z-index:999;}
/* ── Print ── */
@media print{
  /* Use exact screen-match pixel dimensions so font-sizes render identically to browser */
  @page{size:1920px 1080px;margin:0;}
  html,body{overflow:visible;width:1920px;height:1080px;}
  #deck{overflow:visible;height:auto;width:1920px;}
  #pb{display:none!important;}
  .slide{
    position:relative!important;opacity:1!important;transform:none!important;
    pointer-events:auto!important;display:grid!important;
    width:1920px!important;height:1080px!important;
    page-break-after:always;break-after:page;overflow:hidden;
    print-color-adjust:exact;-webkit-print-color-adjust:exact;
  }
  .slide.title-slide{
    display:flex!important;
    print-color-adjust:exact;-webkit-print-color-adjust:exact;
    background-color:var(--navy)!important;
  }
  .s-footer,.s-header{
    print-color-adjust:exact;-webkit-print-color-adjust:exact;
  }
}
"""
def _strip_yaml_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_without_frontmatter)."""
    # Strip UTF-8 BOM if present
    text = text.lstrip("\ufeff")
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            yaml_block = text[3:end].strip()
            body = text[end + 4:].lstrip("\n")
            # minimal YAML parse for key: value lines
            for line in yaml_block.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
            return meta, body
    return meta, text

def _md_inline(text: str) -> str:
    """Convert inline markdown (bold, italic, code, links) to HTML."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Obsidian wikilinks → plain text label
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
    # Markdown links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text

def _md_table_to_html(lines: list[str]) -> str:
    """Convert markdown table lines to an HTML table."""
    rows = []
    for i, line in enumerate(lines):
        line = line.strip().strip("|")
        cells = [c.strip() for c in line.split("|")]
        if all(re.match(r'^[-: ]+$', c) for c in cells if c):
            continue   # separator row
        tag = "th" if i == 0 else "td"
        row_html = "".join(f"<{tag}>{_md_inline(c)}</{tag}>" for c in cells)
        rows.append(f"<tr>{row_html}</tr>")
    return "<table>" + "".join(rows) + "</table>"

# Emoji → .ico colour class mapping
_EMOJI_ICO: dict[str, str] = {
    "🚀": "b", "⚡": "b", "💡": "o", "🎯": "b", "📊": "b", "💻": "b",
    "🛡️": "g", "✅": "g", "🔒": "g", "🏥": "g", "🌿": "g",
    "🔗": "t", "🌐": "t", "📡": "t",
    "🏢": "b", "🤝": "b", "👥": "b",
    "⚠️": "o", "🔥": "o", "⏱️": "o",
    "❌": "r", "🚨": "r",
    "🤖": "p", "🧠": "p", "🔬": "p",
}

def _extract_leading_emoji(text: str) -> tuple[str, str]:
    """Return (emoji, rest_of_text) if text starts with a known emoji, else ('', text)."""
    for emoji in _EMOJI_ICO:
        if text.startswith(emoji):
            return emoji, text[len(emoji):].lstrip()
    return "", text


def _bullets_to_html(lines: list[str]) -> str:
    """Convert bullet lines (- or * or numbered) to nested <ul>/<ol> HTML."""
    result = []
    stack = []  # (indent_level, tag)

    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.lstrip()

        if re.match(r'^(\d+)\. ', stripped):
            tag = "ol"
            content = re.sub(r'^\d+\. ', '', stripped)
        elif stripped.startswith(("- ", "* ", "+ ")):
            tag = "ul"
            content = stripped[2:]
        else:
            # plain paragraph line
            result.append(f"<p>{_md_inline(stripped)}</p>")
            continue

        # Detect leading emoji and render as styled .ico span
        emoji, content_rest = _extract_leading_emoji(content.strip())
        if emoji:
            colour = _EMOJI_ICO[emoji]
            content_html = (
                f'<span class="ico {colour}">{emoji}</span>'
                f'<span class="bt">{_md_inline(content_rest)}</span>'
            )
            li_class = ' class="bullets"' if not stack else ''
        else:
            content_html = _md_inline(content)
            li_class = ''

        if not stack:
            result.append(f'<ul class="bullets">')
            stack.append((indent, "ul"))
        elif indent > stack[-1][0]:
            result.append(f'<ul class="bullets">')
            stack.append((indent, "ul"))
        elif indent < stack[-1][0]:
            while stack and stack[-1][0] > indent:
                _, prev_tag = stack.pop()
                result.append(f"</{prev_tag}>")
            if not stack or stack[-1][0] < indent:
                result.append(f'<ul class="bullets">')
                stack.append((indent, "ul"))

        result.append(f"<li>{content_html}</li>")

    while stack:
        _, t = stack.pop()
        result.append(f"</{t}>")

    return "\n".join(result)

def _encode_image(path: Path) -> str:
    """Return a base64 data URI for an image file."""
    suffix = path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp"}
    mime = mime_map.get(suffix, "image/png")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}"

def _resolve_image(src: str, vault_root: Path, source_dir: Path) -> str:
    """Try to resolve image path to a base64 data URI, or return placeholder."""
    candidates = [
        source_dir / src,
        vault_root / src,
        vault_root / src.lstrip("/"),
    ]
    # Obsidian attachment search: look in vault for filename only
    filename = Path(src).name
    for f in vault_root.rglob(filename):
        candidates.append(f)

    for c in candidates:
        if c.exists():
            try:
                return _encode_image(c)
            except Exception:
                pass
    return ""   # signal: not found

def parse_markdown(text: str, vault_root: Path, source_path: Optional[Path] = None) -> tuple[dict, list[Slide]]:
    """Parse markdown into (frontmatter, [Slide, ...])."""
    meta, body = _strip_yaml_frontmatter(text)
    source_dir = source_path.parent if source_path else vault_root
    slides = []

    # Split into top-level blocks
    lines = body.splitlines()
    blocks = []   # list of (heading_level, heading_text, body_lines)
    current_heading = (0, "", [])

    for line in lines:
        h1 = re.match(r'^# (.+)$', line)
        h2 = re.match(r'^## (.+)$', line)
        h3 = re.match(r'^### (.+)$', line)
        if h1:
            if current_heading[2] or current_heading[1]:
                blocks.append(current_heading)
            current_heading = (1, h1.group(1).strip(), [])
        elif h2:
            if current_heading[2] or current_heading[1]:
                blocks.append(current_heading)
            current_heading = (2, h2.group(1).strip(), [])
        elif h3:
            if current_heading[2] or current_heading[1]:
                blocks.append(current_heading)
            current_heading = (3, h3.group(1).strip(), [])
        else:
            current_heading[2].append(line)

    if current_heading[2] or current_heading[1]:
        blocks.append(current_heading)

    # Cover slide from meta or first H1
    cover_added = False
    for level, title, body_lines in blocks:
        if level == 1 and not cover_added:
            subtitle = ""
            remaining = []
            for bl in body_lines:
                if bl.strip() and not subtitle:
                    subtitle = _md_inline(bl.strip())
                elif bl.strip():
                    remaining.append(bl)
            body_lines = remaining
            slides.append(Slide(
                type="cover",
                title=title,
                subtitle=subtitle,
                meta=meta
            ))
            cover_added = True
            # Any remaining body under H1 becomes a content slide
            if body_lines:
                slides.append(_make_content_slide("", body_lines, vault_root, source_dir))
            continue

        if not cover_added:
            # No H1 found yet — synthesise cover from meta
            slides.append(Slide(type="cover", title=meta.get("title", "Presentation"),
                                subtitle="", meta=meta))
            cover_added = True

        if level == 2:
            if body_lines:
                # H2 with body → single content slide with title in header
                slides.append(_make_content_slide(title, body_lines, vault_root, source_dir))
            else:
                # H2 with no body → section divider slide
                slides.append(Slide(type="section", title=title))
        elif level == 3:
            slides.append(_make_content_slide(title, body_lines, vault_root, source_dir))
        else:
            if body_lines:
                slides.append(_make_content_slide(title, body_lines, vault_root, source_dir))

    if not cover_added:
        slides.insert(0, Slide(type="cover",
                                title=meta.get("title", "Presentation"),
                                subtitle="", meta=meta))
    return meta, slides

def _make_content_slide(title: str, body_lines: list[str], vault_root: Path, source_dir: Path) -> Slide:
    """Convert body_lines into the most appropriate slide type."""
    full = "\n".join(body_lines)

    # Strip any mermaid fences and diagram hint comments — diagrams use inline SVG only
    full = re.sub(r'<!--\s*diagram:[^\-]*-->', '', full)
    full = re.sub(r'```mermaid\s*\n.*?```', '', full, flags=re.DOTALL)

    # Check for blockquote (> …)
    non_empty = [l for l in body_lines if l.strip()]
    if non_empty and all(l.strip().startswith(">") for l in non_empty):
        quote_text = " ".join(l.strip().lstrip(">").strip() for l in non_empty)
        return Slide(type="quote", title=title, body_html=f"<blockquote>{_md_inline(quote_text)}</blockquote>")

    # Check for table
    table_lines = [l for l in body_lines if l.strip().startswith("|")]
    if len(table_lines) >= 2:
        table_html = _md_table_to_html(table_lines)
        return Slide(type="table", title=title, body_html=table_html)

    # Check for image-only slide (Obsidian ![[img]] or ![](path))
    obsidian_img = re.findall(r'!\[\[([^\]]+)\]\]', full)
    md_img = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', full)
    if (obsidian_img or md_img) and len(non_empty) <= 3:
        src = obsidian_img[0] if obsidian_img else md_img[0][1]
        alt = "" if obsidian_img else md_img[0][0]
        data_uri = _resolve_image(src, vault_root, source_dir)
        if data_uri:
            img_html = f'<img src="{data_uri}" alt="{html_module.escape(alt)}" class="slide-image">'
        else:
            img_html = f'<div class="image-placeholder">[ Image: {html_module.escape(src)} ]</div>'
        return Slide(type="image", title=title, body_html=img_html)

    # Generic content slide — bullet list or paragraphs
    bullet_lines = [l for l in body_lines if re.match(r'^\s*[-*+]|\s*\d+\.', l) or l.strip() == ""]
    paragraph_lines = [l for l in body_lines if l.strip() and not re.match(r'^\s*[-*+]|\s*\d+\.', l)]

    if len(bullet_lines) > len(paragraph_lines):
        html_body = _bullets_to_html(body_lines)
    else:
        # Replace inline images with embedded versions
        processed = []
        for line in body_lines:
            # Obsidian embeds
            def replace_obsidian(m):
                src = m.group(1)
                uri = _resolve_image(src, vault_root, source_dir)
                return f'<img src="{uri}" class="inline-image">' if uri else f'[Image: {src}]'
            line = re.sub(r'!\[\[([^\]]+)\]\]', replace_obsidian, line)
            # Markdown images
            def replace_md_img(m):
                alt_t, src = m.group(1), m.group(2)
                uri = _resolve_image(src, vault_root, source_dir)
                return f'<img src="{uri}" alt="{html_module.escape(alt_t)}" class="inline-image">' if uri else f'[Image: {src}]'
            line = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_md_img, line)
            processed.append(line)

        html_body = "".join(
            f"<p>{_md_inline(l.strip())}</p>" if l.strip() else "<br>"
            for l in processed
        )

    return Slide(type="content", title=title, body_html=html_body)

# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------


def render_slide_html(slide: Slide, slide_num: int = 0, total: int = 0, pres_title: str = "") -> str:
    """Wrap a parsed Slide in the mandatory 4-zone layout: header | body[left/right] | footer."""
    footer_html = (
        f'<div class="s-footer">'
        f'<span class="s-footer-title">{html_module.escape(pres_title)}</span>'
        f'<div class="s-footer-nav">'
        f'<button class="nb" onclick="prev()" title="Previous">&#8592;</button>'
        f'<span class="nav-ctr">{slide_num} / {total}</span>'
        f'<button class="nb" onclick="next()" title="Next">&#8594;</button>'
        f'</div>'
        f'<div class="s-footer-brand">'
        f'<span class="phl-footer-copy">&#169; Koninklijke Philips N.V. All rights reserved.</span>'
        f'<img class="phl-footer-logo" src="data:image/png;base64,{_PHL_LOGO_BLUE_B64}" alt="Philips"/>'
        f'</div>'
        f'</div>'
        if slide_num else ""
    )

    if slide.type == "cover":
        subtitle_html = f'\n    <p class="cover-subtitle">{html_module.escape(slide.subtitle)}</p>' if slide.subtitle else ""
        return (
            f'<div class="slide title-slide">\n'
            f'  <div class="cover-content">\n'
            f'    <h1 class="cover-title">{html_module.escape(slide.title)}</h1>{subtitle_html}\n'
            f'  </div>\n'
            f'</div>'
        )

    elif slide.type == "section":
        return (
            f'<div class="slide" style="justify-content:center;align-items:center;">\n'
            f'  <h2 style="font-size:2.2em;font-weight:700;color:var(--navy);">{html_module.escape(slide.title)}</h2>\n'
            f'  <div style="width:60px;height:4px;background:var(--blue);border-radius:2px;margin-top:16px;"></div>\n'
            f'{footer_html}'
            f'</div>'
        )

    else:  # content / quote / table / image
        header_html = (
            f'<div class="s-header">'
            f'<span class="s-header-title">{html_module.escape(slide.title)}</span>'
            f'</div>\n'
            if slide.title else '<div class="s-header"></div>\n'
        )
        return (
            f'<div class="slide">\n'
            f'  {header_html}'
            f'  <div class="s-body">\n'
            f'    <div class="s-left">{slide.body_html}</div>\n'
            f'    <div class="s-right"><div style="color:var(--muted);font-size:.8em;text-align:center;">[ Diagram ]</div></div>\n'
            f'  </div>\n'
            f'  {footer_html}'
            f'</div>'
        )


def _load_strata_css(vault_root: Optional[Path]) -> str:
    """Extract CSS from the Strata Presentation Template. Falls back to COMPONENT_CSS."""
    if vault_root:
        tpl = vault_root / "08 - Templates" / "Strata Presentation Template.html"
        if tpl.exists():
            raw = tpl.read_text(encoding="utf-8")
            m = re.search(r'<style>(.*?)</style>', raw, re.DOTALL)
            if m:
                return m.group(1)
    return COMPONENT_CSS


def build_html(slides_html: str, title: str, vault_root: Optional[Path] = None) -> str:
    """Assemble the full self-contained HTML slide deck."""
    # Resolve cover background image
    cover_bg_style = ""
    if vault_root:
        cover_bg_path = vault_root / "02 - Sources" / "Attachments" / "slide_cover_page_background.png"
        if cover_bg_path.exists():
            data_url = _encode_image(cover_bg_path)
            cover_bg_style = f"background-image:url('{data_url}');background-size:cover;background-position:center;"

    # Inject cover background on both class names used by different slide formats
    if cover_bg_style:
        slides_html = slides_html.replace(
            '<div class="slide title-slide">',
            f'<div class="slide title-slide" style="{cover_bg_style}">',
            1
        )
        slides_html = slides_html.replace(
            '<div class="slide cover">',
            f'<div class="slide cover" style="{cover_bg_style}">',
            1
        )

    deck_js = r"""
const slides = document.querySelectorAll('.slide');
const pb     = document.getElementById('pb');
const dotsEl = document.getElementById('dots');
let   cur    = 0;
if (dotsEl) {
  slides.forEach((_,i) => {
    const d = document.createElement('div');
    d.className = 'dot' + (i===0?' active':'');
    d.onclick = () => goTo(i);
    dotsEl.appendChild(d);
  });
}
function goTo(n) {
  if (n < 0 || n >= slides.length) return;
  slides[cur].classList.remove('active');
  slides[cur].classList.add('exit');
  const old = cur;
  setTimeout(() => slides[old].classList.remove('exit'), 400);
  cur = n;
  slides[cur].classList.add('active');
  if (dotsEl) document.querySelectorAll('.dot').forEach((d,i) => d.classList.toggle('active', i===cur));
  if (pb) pb.style.width = ((cur+1)/slides.length*100)+'%';
  document.querySelectorAll('.nav-ctr').forEach(el => el.textContent = (cur+1)+' / '+slides.length);
}
function go(d)  { goTo(cur + d); }
function next() { go(1); }
function prev() { go(-1); }
document.addEventListener('keydown', e => {
  if (e.key==='ArrowRight'||e.key===' ')        { e.preventDefault(); go(1); }
  if (e.key==='ArrowLeft'||e.key==='Backspace') { e.preventDefault(); go(-1); }
  if (e.key==='Home') goTo(0);
  if (e.key==='End')  goTo(slides.length-1);
});
let tx = 0;
document.addEventListener('touchstart', e => { tx = e.touches[0].clientX; });
document.addEventListener('touchend',   e => { const dx=e.changedTouches[0].clientX-tx; if(dx<-50)go(1); if(dx>50)go(-1); });
goTo(0);
"""

    slide_css = _load_strata_css(vault_root)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_module.escape(title)}</title>
  <style>{slide_css}</style>
  <style>{_PHL_FOOTER_CSS}</style>
</head>
<body>
  <div id="deck">
{slides_html}
  </div>
  <div id="pb" style="width:{100//max(1,1)}%"></div>
  <script>{deck_js}</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate self-contained offline HTML presentation (custom standalone deck)")
    parser.add_argument("--source",     required=True, help="Path to source markdown/HTML, or '-' for stdin")
    parser.add_argument("--title",      default="",    help="Override presentation title")
    parser.add_argument("--output-dir", default="",    help="Output directory (default: 07 - Writing/presentations)")
    parser.add_argument("--vault-path", default=str(VAULT_ROOT), help="Vault root path")
    args = parser.parse_args()

    vault_root = Path(args.vault_path)

    # Read source
    if args.source == "-":
        text = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        source_path = None
    else:
        source_path = Path(args.source)
        if not source_path.is_absolute():
            source_path = vault_root / args.source
        with open(source_path, encoding="utf-8") as f:
            text = f.read()

    # HTML passthrough mode: if input is already slide HTML, skip markdown parsing
    stripped = text.strip()
    if stripped.startswith("<section") or stripped.startswith("<!--") or stripped.startswith('<div class="slide'):
        pres_title = args.title or "Presentation"
        # 1. Convert <section> tags to <div class="slide">
        slides_html = re.sub(r'<section\s+class="([^"]*)"', r'<div class="slide \1"', text)
        slides_html = re.sub(r'<section(?:\s*/?>|>)', '<div class="slide">', slides_html)
        slides_html = slides_html.replace('</section>', '</div>')
        # 2. Remap old class names → mandatory 4-zone names
        slides_html = slides_html.replace('class="s-head"',       'class="s-header"')
        slides_html = slides_html.replace('class="s-head-title"', 'class="s-header-title"')
        slides_html = slides_html.replace('class="s-head-label"', 'class="s-header-label"')
        slides_html = re.sub(r'class="col col-wide"',   'class="s-left"',  slides_html)
        slides_html = re.sub(r'class="col col-narrow"', 'class="s-right"', slides_html)
        # 3. Inject per-slide footer (slide N / total + title) before each closing </div> of a .slide
        slide_divs = re.split(r'(?=<div class="slide(?:\s[^"]*)?">)', slides_html)
        slide_divs = [s for s in slide_divs if s.strip()]
        total_slides = len(slide_divs)
        rebuilt = []
        for idx, sd in enumerate(slide_divs):
            n = idx + 1
            is_cover = 'title-slide' in sd[:80] or ' cover"' in sd[:80] or " cover'" in sd[:80]
            if not is_cover and '</div>' in sd and 's-footer' not in sd:
                footer = (
                    f'<div class="s-footer">'
                    f'<span class="s-footer-title">{html_module.escape(pres_title)}</span>'
                    f'<div class="s-footer-nav">'
                    f'<button class="nb" onclick="prev()" title="Previous">&#8592;</button>'
                    f'<span class="nav-ctr">{n} / {total_slides}</span>'
                    f'<button class="nb" onclick="next()" title="Next">&#8594;</button>'
                    f'</div>'
                    f'<div class="s-footer-brand">'
                    f'<span class="phl-footer-copy">&#169; Koninklijke Philips N.V. All rights reserved.</span>'
                    f'<img class="phl-footer-logo" src="data:image/png;base64,{_PHL_LOGO_BLUE_B64}" alt="Philips"/>'
                    f'</div>'
                    f'</div>'
                )
                # Insert footer before the last closing </div> of the slide
                last_div = sd.rfind('</div>')
                sd = sd[:last_div] + footer + sd[last_div:]
            rebuilt.append(sd)
        slides_html = "\n".join(rebuilt)
    else:
        # Parse markdown
        meta, slides = parse_markdown(text, vault_root, source_path)

        if not slides:
            print(json.dumps({"success": False, "error": "No slides could be parsed from source"}))
            sys.exit(1)

        # Title — prefer H1 from cover slide, then frontmatter, then filename
        pres_title = args.title
        if not pres_title:
            if slides[0].type == "cover" and slides[0].title:
                pres_title = slides[0].title
            elif meta.get("title"):
                pres_title = meta["title"]
            elif source_path:
                pres_title = source_path.stem
            else:
                pres_title = "Presentation"
        if slides[0].type == "cover" and not slides[0].title:
            slides[0].title = pres_title

        slides_html = "\n".join(
            render_slide_html(s, slide_num=i+1, total=len(slides), pres_title=pres_title)
            for i, s in enumerate(slides)
        )

    # Build HTML
    html_content = build_html(slides_html, pres_title, vault_root=vault_root)

    # Output path — §VII: filename = title, no date prefix
    out_dir_str = args.output_dir or str(vault_root / OUTPUT_DIR_NAME)
    out_dir = Path(out_dir_str)
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_title = re.sub(r'[<>:"/\\|?*]', '', pres_title).strip()
    out_path = out_dir / f"{safe_title}.html"
    out_path.write_text(html_content, encoding="utf-8")
    file_size_kb = round(out_path.stat().st_size / 1024, 1)

    warnings = []
    if not stripped.startswith("<section") and not stripped.startswith("<!--") and not stripped.startswith('<div class="slide'):
        if len(slides) > 30:
            warnings.append(f"Large presentation: {len(slides)} slides generated.")

    result = {
        "success": True,
        "path": str(out_path),
        "title": pres_title,
        "slide_count": slides_html.count('<div class="slide'),
        "file_size_kb": file_size_kb,
    }
    if warnings:
        result["warnings"] = warnings

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
