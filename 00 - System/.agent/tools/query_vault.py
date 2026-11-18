#!/usr/bin/env python3
"""
LangChain-free FAISS query tool.
Loads index.faiss + metadata.jsonl and returns top-k passages as JSON.

Usage:
 .\\"00 - System"\\.agent\\venv\\Scripts\\python.exe ".\\00 - System\\.agent\\tools\\query_vault.py" "your question" [k]
 .\\"00 - System"\\.agent\\venv\\Scripts\\python.exe ".\\00 - System\\.agent\\tools\\query_vault.py" "your question" --k 3
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import FAISS_STORE, MODEL_PATH


def load_metadata_jsonl(path: Path) -> List[Dict]:
    metas = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            metas.append(json.loads(line))
    return metas


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Semantic search over the vault FAISS index."
    )
    parser.add_argument("question", help="Natural-language query")
    parser.add_argument("k", nargs="?", type=int, default=None, help="Number of results (default 5)")
    parser.add_argument("--k", dest="k_option", type=int, default=None, help="Number of results (default 5)")
    parser.add_argument("--persist", default=FAISS_STORE, help="Directory containing index.faiss + metadata.jsonl.")
    parser.add_argument("--model", default=MODEL_PATH, help="Sentence-transformers model directory.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    question = args.question
    k = args.k_option if args.k_option is not None else (args.k if args.k is not None else 5)
    if k < 1:
        print(json.dumps({"error": "k must be >= 1"}))
        sys.exit(2)

    persist_dir = Path(args.persist)
    model_path  = args.model

    index_path = persist_dir / "index.faiss"
    meta_path  = persist_dir / "metadata.jsonl"

    if not index_path.exists() or not meta_path.exists():
        print(json.dumps({"error": "Missing index.faiss or metadata.jsonl", "persist_dir": str(persist_dir)}))
        sys.exit(2)

    index = faiss.read_index(str(index_path))
    metas = load_metadata_jsonl(meta_path)

    model = SentenceTransformer(model_path)
    q = model.encode([question], convert_to_numpy=True, normalize_embeddings=True).astype("float32")

    scores, ids = index.search(q, k)
    scores = scores[0].tolist()
    ids    = ids[0].tolist()

    out = []
    for score, idx in zip(scores, ids):
        if idx < 0 or idx >= len(metas):
            continue
        meta = metas[idx]
        out.append({
            "score": float(score),
            "text":  meta.get("text", ""),
            "metadata": {
                "file_path": meta.get("file_path"),
                "rel_path":  meta.get("rel_path"),
                "heading":   meta.get("heading"),
                "block_id":  meta.get("block_id"),
                "file_sha1": meta.get("file_sha1"),
                "note_type": meta.get("note_type", ""),
                "subject":   meta.get("subject", ""),
                "topic":     meta.get("topic", ""),
            }
        })

    sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")


if __name__ == "__main__":
    main()