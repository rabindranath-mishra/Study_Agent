#!/usr/bin/env python3
"""
LangChain-free FAISS query tool.
Loads index.faiss + metadata.jsonl and returns top-k passages as JSON.

Usage:
 .\\"00 - System"\\.agent\\venv\\Scripts\\python.exe ".\\00 - System\\.agent\\tools\\query_vault.py" "your question" [k]
"""

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


def main():
    if len(sys.argv) < 2:
        print('Usage: python query_vault.py "question" [k]')
        sys.exit(1)

    question = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    persist_dir = Path(FAISS_STORE)
    model_path  = MODEL_PATH

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

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()