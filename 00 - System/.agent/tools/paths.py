"""
paths.py — Vault-portable path constants for all agent tools.

All paths are derived from this file's location, so the vault can be moved
or cloned to any directory without any hardcoded paths breaking.

Layout (relative to this file):
    vault_root / "00 - System" / ".agent" / "tools" / paths.py
"""

from pathlib import Path as _Path

_TOOLS_DIR = _Path(__file__).resolve().parent       # 00 - System/.agent/tools/
_AGENT_DIR = _TOOLS_DIR.parent                      # 00 - System/.agent/
_SYSTEM_DIR = _AGENT_DIR.parent                     # 00 - System/
_VAULT_ROOT = _SYSTEM_DIR.parent                    # vault root

# ── Agent infrastructure ──────────────────────────────────────────────────────
VAULT_ROOT  = str(_VAULT_ROOT)
FAISS_STORE = str(_AGENT_DIR / "faiss_store")
MODEL_PATH  = str(_AGENT_DIR / "models" / "all-MiniLM-L6-v2")
PYTHON_EXE  = str(_AGENT_DIR / "venv" / "Scripts" / "python.exe")

# ── State & logs (constitution §XIV) ─────────────────────────────────────────
STATE_DIR   = str(_AGENT_DIR / "state")
LOGS_DIR    = str(_AGENT_DIR / "logs")
SESSION_LOG = str(_AGENT_DIR / "logs" / "session_log.jsonl")

# ── PowerShell helpers ────────────────────────────────────────────────────────
PS_SCRIPT_CREATE_NOTE = str(_TOOLS_DIR / "create_note_stdin.ps1")

# ── Vault folders ─────────────────────────────────────────────────────────────
SYSTEM_DIR    = str(_SYSTEM_DIR)                        # same as 00 - System/
INBOX_DIR     = str(_VAULT_ROOT / "01 - Inbox")
SOURCES_DIR   = str(_VAULT_ROOT / "02 - Sources")
SUBJECTS_DIR  = str(_VAULT_ROOT / "03 - Subjects")
CONCEPTS_DIR  = str(_VAULT_ROOT / "04 - Concepts")
PRACTICE_DIR  = str(_VAULT_ROOT / "05 - Practice")
PLANS_DIR     = str(_VAULT_ROOT / "06 - Plans")
OUTPUTS_DIR   = str(_VAULT_ROOT / "07 - Outputs")
TEMPLATES_DIR = str(_VAULT_ROOT / "08 - Templates")
ARCHIVE_DIR   = str(_VAULT_ROOT / "99 - Archive")
