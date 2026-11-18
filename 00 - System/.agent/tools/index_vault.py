#!/usr/bin/env python3
"""
LangChain-free Obsidian vault indexer (FAISS + sentence-transformers).
- Parses YAML frontmatter for note_type, subject, topic metadata  [G16]
- Extracts heading sections + Obsidian block anchors (^blockid)
- Chunks text with correct overlap
- Embeds with local sentence-transformers model
- Saves FAISS index + metadata.jsonl (including passage text)     [G17]

Usage (PowerShell):
 .\\"00 - System"\\.agent\\venv\\Scripts\\python.exe ".\\00 - System\\.agent\\tools\\index_vault.py" [--rebuild]

The index is always rebuilt from scratch; --rebuild is accepted for
compatibility with the documented setup/update commands.
"""

import argparse
import sys
import json
import re
import hashlib
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import VAULT_ROOT, FAISS_STORE, MODEL_PATH


RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", flags=re.MULTILINE)
RE_BLOCK = re.compile(r"\^(?P<id>[A-Za-z0-9\-_]+)")
RE_FRONTMATTER = re.compile(
    r"^\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n",
    flags=re.DOTALL
)

EXCLUDED_DIRS = {".agent", ".obsidian", ".git"}


def parse_frontmatter(text: str) -> Dict[str, str]:
    """Extract note_type, subject, and topic from YAML frontmatter block."""
    m = RE_FRONTMATTER.match(text)
    if not m:
        return {}
    result = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip().strip('"').strip("'")
            if key in ("type", "subject", "topic"):
                result[key] = val
    return result


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block so it is not chunked as content."""
    return RE_FRONTMATTER.sub("", text, count=1)


def iter_markdown_files(vault: Path) -> List[Path]:
    results = []
    for md in vault.rglob("*.md"):
        rel = md.relative_to(vault)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        results.append(md)
    return sorted(results)


def split_into_sections(text: str) -> List[Tuple[Optional[str], str]]:
    """
    Split markdown into sections keyed by the most recent heading.
    Returns list[(heading, section_text)] where heading=None means pre-heading content.
    """
    sections: List[Tuple[Optional[str], str]] = []
    last_pos = 0
    last_heading: Optional[str] = None

    for m in RE_HEADING.finditer(text):
        start = m.start()
        chunk = text[last_pos:start].strip()
        if chunk:
            sections.append((last_heading, chunk))
        last_heading = m.group(2).strip()
        last_pos = m.end()

    tail = text[last_pos:].strip()
    if tail:
        sections.append((last_heading, tail))

    return sections


def find_first_block_id(text: str) -> Optional[str]:
    m = RE_BLOCK.search(text)
    return m.group("id") if m else None


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def chunk_text(text: str, chunk_size: int = 900, chunk_overlap: int = 150) -> List[str]:
    """
    Simple stable chunker (no LangChain).
    Splits on paragraph boundaries first, then falls back to hard slicing if needed.
    """
    text = text.strip()
    if not text:
        return []

    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: List[str] = []
    buf: List[str] = []
    buf_len = 0

    def flush():
        nonlocal buf, buf_len
        if buf:
            chunks.append("\n\n".join(buf).strip())
            buf = []
            buf_len = 0

    for p in paras:
        p_len = len(p)
        if buf_len + p_len + (2 if buf else 0) <= chunk_size:
            buf.append(p)
            buf_len += p_len + (2 if buf_len else 0)
        else:
            flush()
            if p_len > chunk_size:
                step = max(chunk_size - chunk_overlap, 1)
                start = 0
                while start < p_len:
                    end = min(start + chunk_size, p_len)
                    chunks.append(p[start:end].strip())
                    if end >= p_len:
                        break
                    start += step
            else:
                buf.append(p)
                buf_len = p_len

    flush()

    # Apply overlap between paragraph-boundary chunks
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped = []
        for i, ch in enumerate(chunks):
            if i == 0:
                overlapped.append(ch)
                continue
            prev = overlapped[-1]
            tail = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
            overlapped.append((tail + "\n" + ch).strip())
        chunks = overlapped

    return [c for c in chunks if c]


def file_sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build_passages(vault_dir: str, chunk_size: int = 900, chunk_overlap: int = 150) -> List[Dict]:
    # Named constants for magic numbers used in chunking
    MIN_CHUNK_LENGTH = 20   # skip trivial chunks (e.g. bare "---" thematic breaks)

    vault = Path(vault_dir).expanduser().resolve()
    items: List[Dict] = []
    skipped_files = 0

    for md in iter_markdown_files(vault):
        try:
            raw = md.read_text(encoding="utf-8")
        except Exception:
            try:
                raw = md.read_text(encoding="latin-1")
            except Exception:
                print(f"[WARN] Could not read {md}, skipping.", file=sys.stderr)
                skipped_files += 1
                continue

        frontmatter = parse_frontmatter(raw)
        text = strip_frontmatter(raw)
        sections = split_into_sections(text)
        sha = file_sha1(md)

        # is_relative_to() added in Python 3.9; use try/except for safety
        try:
            rel_path = str(md.relative_to(vault)) if md.is_relative_to(vault) else str(md)
        except AttributeError:
            try:
                rel_path = str(md.relative_to(vault))
            except ValueError:
                rel_path = str(md)

        for heading, sec_text in sections:
            sec_text = sec_text.strip()
            if not sec_text:
                continue

            block_id = find_first_block_id(sec_text)

            for chunk in chunk_text(sec_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap):
                normalized = normalize_whitespace(chunk)
                if len(normalized) < MIN_CHUNK_LENGTH:
                    continue
                items.append({
                    "text": normalized,
                    "metadata": {
                        "file_path": str(md),
                        "rel_path":  rel_path,
                        "heading":   heading,
                        "block_id":  block_id,
                        "file_sha1": sha,
                        "note_type": frontmatter.get("type", ""),
                        "subject":   frontmatter.get("subject", ""),
                        "topic":     frontmatter.get("topic", ""),
                    }
                })

    if skipped_files:
        print(f"[WARN] Skipped {skipped_files} unreadable file(s) during indexing.", file=sys.stderr)

    return items


def embed_texts(model: SentenceTransformer, texts: List[str], batch_size: int = 64) -> np.ndarray:
    # Normalize embeddings so inner product = cosine similarity
    emb = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")
    return emb


def save_index(persist_dir: Path, index: faiss.Index, passages: List[Dict], config: Dict):
    persist_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(persist_dir / "index.faiss"))

    with (persist_dir / "metadata.jsonl").open("w", encoding="utf-8") as f:
        for p in passages:
            # Store text alongside metadata so query_vault can return full passage content
            f.write(json.dumps({"text": p["text"], **p["metadata"]}, ensure_ascii=False) + "\n")

    with (persist_dir / "index_metadata.json").open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the FAISS semantic index for the vault."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the index from scratch (this is always the behaviour).",
    )
    parser.add_argument("--vault", default=VAULT_ROOT, help="Vault root directory.")
    parser.add_argument("--persist", default=FAISS_STORE, help="Directory for index.faiss + metadata.jsonl.")
    parser.add_argument("--model", default=MODEL_PATH, help="Sentence-transformers model directory.")
    parser.add_argument("--chunk-size", type=int, default=900, help="Chunk size in characters (default 900).")
    parser.add_argument("--chunk-overlap", type=int, default=150, help="Chunk overlap in characters (default 150).")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    vault_path  = args.vault
    persist_dir = Path(args.persist)
    model_path  = args.model

    chunk_size    = args.chunk_size
    chunk_overlap = args.chunk_overlap

    print(f"Vault:           {vault_path}")
    print(f"Persist:         {persist_dir}")
    print(f"Embedding model: {model_path}")
    print(f"Chunking:        size={chunk_size}, overlap={chunk_overlap}")

    passages = build_passages(vault_path, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not passages:
        print("[ERROR] No passages found. Check vault path and markdown files.")
        sys.exit(2)

    texts = [p["text"] for p in passages]

    model = SentenceTransformer(model_path)

    print(f"Embedding {len(texts)} passages...")
    vectors = embed_texts(model, texts)

    dim = vectors.shape[1]
    print(f"Embedding dim: {dim}")

    # Inner Product index (works as cosine because vectors are normalized)
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    config = {
        "vault_path":     str(Path(vault_path).expanduser().resolve()),
        "persist_dir":    str(persist_dir),
        "embedding_model": model_path,
        "embedding_dim":  dim,
        "num_passages":   len(texts),
        "chunk_size":     chunk_size,
        "chunk_overlap":  chunk_overlap,
        "faiss_index":    "IndexFlatIP (cosine via normalized embeddings)",
        "metadata_file":  "metadata.jsonl",
    }

    print("Saving index + metadata...")
    save_index(persist_dir, index, passages, config)
    print("Done.")


if __name__ == "__main__":
    main()