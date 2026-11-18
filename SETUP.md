# Setup Guide — Study Agent System

Complete setup instructions for installing and configuring the Study Agent vault.

---

## Prerequisites

| Tool | Version | Required for |
|------|---------|--------------|
| [PowerShell](https://github.com/PowerShell/PowerShell/releases) | 7.5+ recommended (5.1 works) | Setup script |
| [Python](https://www.python.org/downloads/) | 3.14+ | All vault tools |
| [Git](https://git-scm.com/) | Any | Cloning / updating |
| [Obsidian](https://obsidian.md/) | 1.4+ | Vault UI + agent panel |
| [GitHub Copilot CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli) | Latest | Agent runtime |
| [Node.js](https://nodejs.org/) | 20+ | Optional — `sarvam-chat.mjs` only |

### API keys

| Key | Required? | Used by |
|-----|-----------|---------|
| `TAVILY_API_KEY` | Optional | `web_search_agent.py` (web research) |
| `SARVAM_API_KEY` | Optional | `sarvam-chat.mjs` (standalone chat script) |

The vault works fully offline without either key; only web research and the
standalone Sarvam chat script are disabled.

> **No Git LFS required.** The embedding model is committed as
> `00 - System/.agent/models/all-miniLM-L6-v2.zip` (≈83 MB) and extracted by
> the setup script.

---

## 1. Get the repository

```powershell
git clone https://github.com/rabindranath-mishra/Study_Agent.git
cd Study_Agent
```

Downloading the ZIP from GitHub works too if you do not plan to contribute.

---

## 2. Run setup

From the vault root:

```powershell
& ".\00 - System\.agent\setup_windows.ps1"
```

The script derives every path from its own location, so it also works when run
from `00 - System\.agent`.

### Switches

| Switch | Effect |
|--------|--------|
| `-SkipIndex` | Do not build the FAISS index |
| `-Reindex` | Rebuild the index even if one already exists |
| `-SkipTests` | Skip the pytest run |
| `-NonInteractive` | Never prompt for API keys (CI / unattended runs) |

Example:

```powershell
& ".\00 - System\.agent\setup_windows.ps1" -Reindex -SkipTests
```

### What the script does

1. ✅ Checks Python 3.14+
2. ✅ Verifies the 10-folder vault skeleton and `00 - System\study.agent.md`
3. ✅ Extracts the embedding model from `models\all-miniLM-L6-v2.zip`
4. ✅ Creates `00 - System\.agent\venv`
5. ✅ Installs `00 - System\.agent\tools\requirements.txt` plus `pytest`
6. ✅ Converts `pytorch_model.bin` → `model.safetensors` when needed
7. ✅ Configures `TAVILY_API_KEY` (optional, Windows user environment)
8. ✅ Configures `SARVAM_API_KEY` in the vault-root `.env` (optional)
9. ✅ Checks Node.js and the global `sarvamai` SDK (optional)
10. ✅ Builds the FAISS index in `00 - System\.agent\faiss_store`
11. ✅ Verifies semantic search with a test query
12. ✅ Runs the pytest suite

### Expected output (abridged)

```
▶  Checking Python...
  ✅  Python 3.14.3 detected

▶  Verifying vault skeleton...
  ✅  All 10 vault folders present
  ✅  Agent definition found: 00 - System\study.agent.md

▶  Checking embedding model...
  ✅  Embedding model already present at: ...\models\all-MiniLM-L6-v2

▶  Building FAISS semantic search index...
  ✅  Vault indexed successfully

▶  Verifying installation with a test query...
  ✅  Semantic search working — vault is queryable

▶  Running the test suite...
  ✅  All tests passed
```

---

## 3. Configure API keys manually (optional)

### Tavily (web research)

```powershell
# Current session only
$env:TAVILY_API_KEY = "tvly-xxxxxxxxxxxxxxxxxxxxx"

# Persistent (Windows user environment)
[System.Environment]::SetEnvironmentVariable("TAVILY_API_KEY", "tvly-xxxxxxxxxxxxxxxxxxxxx", "User")
```

Get a free key at <https://tavily.com>.

### Sarvam (standalone chat script)

Create `.env` in the vault root:

```dotenv
SARVAM_API_KEY=your-key-here
```

`.env` is gitignored. `sarvam-chat.mjs` also needs the SDK:

```powershell
npm install -g sarvamai
node .\sarvam-chat.mjs
```

---

## 4. Open in Obsidian

1. Launch Obsidian → **Open folder as vault** → select the `Study_Agent` folder.
2. Trust the vault and disable Restricted Mode.
3. Enable the **Copilot ACP Agent** community plugin.
4. Configure it under **Settings → Copilot ACP Agent**:

```json
{
  "copilotPath": "C:\\Users\\<you>\\AppData\\Roaming\\npm\\copilot.cmd",
  "host": "127.0.0.1",
  "port": 9000,
  "vaultPath": "<absolute path to this vault>",
  "openOnStartup": false,
  "model": "<a model available to your Copilot CLI>",
  "showSystemLogs": false,
  "extraCliArgs": "--yolo",
  "promptPrefixText": "Start as an agent as per the instructions in",
  "promptPresetsText": "study.agent.md"
}
```

> `copilotPath` and `vaultPath` are machine-specific. Do not commit your local
> `data.json` if you customize it.

---

## 5. Verify the installation

```powershell
$py = ".\00 - System\.agent\venv\Scripts\python.exe"
```

### Semantic search

```powershell
& $py ".\00 - System\.agent\tools\query_vault.py" "photosynthesis" 3
```

Returns a JSON array. Each result has `score`, `text`, and `metadata`
(`file_path`, `rel_path`, `heading`, `block_id`, `file_sha1`, `note_type`,
`subject`, `topic`):

```json
[
  {
    "score": 0.63,
    "text": "Photosynthesis is the process...",
    "metadata": {
      "file_path": "D:\\...\\04 - Concepts\\Photosynthesis.md",
      "rel_path": "04 - Concepts\\Photosynthesis.md",
      "heading": "Overview",
      "block_id": null,
      "file_sha1": "...",
      "note_type": "concept",
      "subject": "Biology",
      "topic": "Photosynthesis"
    }
  }
]
```

### Fact checker (Gate 1)

```powershell
& $py ".\00 - System\.agent\tools\fact_checker_agent.py" --claims '["The Earth orbits the Sun"]'
```

```json
{
  "claims_checked": 1,
  "pass": true,
  "violations": [],
  "vault_verdict": "CLEAR",
  "web_checked": false
}
```

### Compliance checker (Gate 2)

```powershell
$content = @"
---
type: concept
subject: Biology
topic: Photosynthesis
generated_by: study
---

# Photosynthesis

Photosynthesis converts light energy into chemical energy.
"@

& $py ".\00 - System\.agent\tools\compliance_agent.py" --title "Photosynthesis" --content $content --note-type concept
```

```json
{
  "status": "PASS",
  "violations": [],
  "checks_run": 10,
  "violation_count": 0
}
```

### Test suite

```powershell
& $py -m pytest ".\00 - System\.agent\tests" -q
```

---

## 6. Troubleshooting

### Python version too old

**Error:** `Python 3.14+ required`

- Install Python 3.14+ from <https://python.org/downloads/>
- Ensure the new interpreter is first on `PATH`
- Restart the terminal and re-run setup

### FAISS installation fails

- `& $py -m pip install --upgrade pip`
- On Windows, install the Visual C++ Build Tools
- Alternative: `conda install -c pytorch faiss-cpu`

### Embedding model not found

The zip must be at:

```
00 - System\.agent\models\all-miniLM-L6-v2.zip
```

It extracts to `00 - System\.agent\models\all-MiniLM-L6-v2\`. If extraction
fails, unzip it manually and rename the extracted `all-MiniLM-L6-v2.pt` folder
to `all-MiniLM-L6-v2`.

### Safetensors conversion fails

```powershell
& $py -m pip install --upgrade torch safetensors
```

Then re-run setup. PyTorch 2.6+ refuses to load `.bin` pickles by default, so
`model.safetensors` is required.

### Rebuild the index

```powershell
& $py ".\00 - System\.agent\tools\index_vault.py" --rebuild
```

The index is always rebuilt from scratch; `--rebuild` is accepted for clarity.

### Tavily returns 401

- Re-copy the key with no leading/trailing spaces
- Confirm it starts with `tvly-`
- Verify the variable is visible: `$env:TAVILY_API_KEY`

### `sarvam-chat.mjs` fails

- Confirm `.env` exists in the vault root and contains `SARVAM_API_KEY=...`
- Install the SDK globally: `npm install -g sarvamai`
- Check Node.js: `node --version`

### PowerShell blocks the script

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Long paths on Windows

```powershell
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

---

## 7. Updating

```powershell
git pull origin main
& ".\00 - System\.agent\setup_windows.ps1" -Reindex
```

`-Reindex` reinstalls nothing that is already present; it refreshes the FAISS
index so new notes become searchable.

---

## 8. Next steps

1. **Read the governance documents**
   - [Vault Constitution](00%20-%20System/Vault%20Constitution.md)
   - [Agent Architecture (C4+1)](00%20-%20System/Agent%20Architecture%20%28C4%2B1%29.md)

2. **Run the study agent**

   ```powershell
   copilot agent run "00 - System\study.agent.md"
   ```

   Or open the Copilot ACP Agent panel in Obsidian.

3. **Create notes through the agent**

   Vault notes must go through the three-gate pipeline:

   ```
   fact_checker_agent.py  →  compliance_agent.py  →  note_writer_agent.py
   ```

   Do not write vault markdown directly with `create_note.py` or an editor.

4. **Customize templates**

   Edit the files in `08 - Templates/` to match your learning style.

---

**Installation time:** ~5–10 minutes (plus ~2–3 minutes for the test suite)
**Disk space:** ~2 GB (model + dependencies)
**Internet:** Required for setup and web research; vault tools work offline afterwards.
