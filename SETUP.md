# Setup Guide - Study Agent System

Complete setup instructions for installing and configuring the Study Agent System.

## Prerequisites

### Required Software

1. **Python 3.14 or later**
   - Download from [python.org](https://www.python.org/downloads/)
   - Verify installation: `python --version`
   - Ensure pip is included: `pip --version`

2. **Obsidian**
   - Download from [obsidian.md](https://obsidian.md/)
   - Version 1.4+ recommended
   - Install on your platform (Windows, macOS, Linux)

3. **Git** (optional, for cloning)
   - Download from [git-scm.com](https://git-scm.com/)
   - Verify installation: `git --version`

### API Keys

4. **Tavily API Key** (for web research)
   - Sign up at [tavily.com](https://tavily.com/)
   - Free tier available for testing
   - Note your API key for configuration

## Installation

### Step 1: Get the Repository

**Option A: Clone with Git**
```bash
git clone https://github.com/yourusername/Study_Agent.git
cd Study_Agent
```

**Option B: Download ZIP**
1. Download ZIP from GitHub
2. Extract to desired location
3. Navigate to folder in terminal

### Step 2: Run Setup Script

**Windows:**
```powershell
cd "00 - System\.agent"
.\setup_windows.ps1
```

**macOS/Linux:**
```bash
cd "00 - System/.agent"
chmod +x setup_unix.sh
./setup_unix.sh
```

The setup script will:
- ✅ Verify Python 3.14+ installation
- ✅ Extract embedding model from zip
- ✅ Create Python virtual environment
- ✅ Install all dependencies from requirements.txt
- ✅ Convert PyTorch model to safetensors format
- ✅ Build FAISS semantic search index
- ✅ Run verification tests

**Expected output:**
```
Checking Python version...
✓ Python 3.14.1 found

Creating virtual environment...
✓ Virtual environment created

Installing dependencies...
✓ Dependencies installed

Building FAISS index...
✓ Index built successfully (1,234 passages indexed)

Running verification...
✓ All tests passed

Setup complete!
```

### Step 3: Configure API Keys

**Windows:**
```powershell
# Temporary (current session only)
$env:TAVILY_API_KEY = "tvly-xxxxxxxxxxxxxxxxxxxxx"

# Permanent (add to PowerShell profile)
notepad $PROFILE
# Add line: $env:TAVILY_API_KEY = "tvly-xxxxxxxxxxxxxxxxxxxxx"
```

**macOS/Linux:**
```bash
# Temporary (current session only)
export TAVILY_API_KEY="tvly-xxxxxxxxxxxxxxxxxxxxx"

# Permanent (add to .bashrc or .zshrc)
echo 'export TAVILY_API_KEY="tvly-xxxxxxxxxxxxxxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc
```

**Alternative: .env file**
```bash
cd "00 - System/.agent"
echo "TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxx" > .env
```

### Step 4: Open in Obsidian

1. Launch Obsidian
2. Click "Open folder as vault"
3. Navigate to `Study_Agent` folder
4. Select folder and click "Open"

**First-time setup in Obsidian:**
- Trust the vault when prompted
- Disable restricted mode if needed
- Install community plugins (when Copilot plugin available)

## Verification

### Test Semantic Search

```bash
cd "00 - System/.agent"

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Test query
python tools/query_vault.py "photosynthesis"
```

**Expected output:**
```json
{
  "results": [
    {
      "passage": "Photosynthesis is the process...",
      "source": "04 - Concepts/Photosynthesis.md",
      "score": 0.87
    }
  ]
}
```

### Test Fact Checker

```bash
python tools/fact_checker_agent.py "The Earth is flat"
```

**Expected output:**
```json
{
  "status": "FAILED",
  "reason": "Contradicts established scientific consensus",
  "confidence": 1.0
}
```

### Test Compliance

```bash
python tools/compliance_agent.py "04 - Concepts/Test.md"
```

**Expected output:**
```json
{
  "status": "PASS",
  "issues": []
}
```

## Troubleshooting

### Common Issues

#### 1. Python Version Too Old

**Error:** `Python 3.14+ required, found 3.12`

**Solution:**
- Install Python 3.14+ from python.org
- Update PATH to prioritize new Python version
- Restart terminal/PowerShell
- Verify: `python --version`

#### 2. FAISS Installation Fails

**Error:** `Could not install faiss-cpu`

**Solution:**
- Ensure pip is up to date: `pip install --upgrade pip`
- Try alternative: `conda install -c pytorch faiss-cpu`
- On Windows, ensure Visual C++ Build Tools installed

#### 3. PyTorch Model Conversion Error

**Error:** `Safetensors conversion failed`

**Solution:**
- Ensure safetensors package installed: `pip install safetensors`
- Check disk space (models ~500MB)
- Try manual conversion:
  ```bash
  python -c "from safetensors.torch import save_file; import torch; ..."
  ```

#### 4. Embedding Model Not Found

**Error:** `Model zip file not found`

**Solution:**
- Check if `all-MiniLM-L6-v2.zip` exists in `00 - System/.agent/`
- Re-download from releases
- Extract manually if needed

#### 5. Tavily API Key Invalid

**Error:** `401 Unauthorized - Invalid API key`

**Solution:**
- Verify key copied correctly (no extra spaces)
- Check key hasn't expired
- Generate new key from tavily.com dashboard
- Ensure environment variable set correctly

#### 6. FAISS Index Build Fails

**Error:** `IndexError: list index out of range`

**Solution:**
- Ensure vault has some notes with content
- Check notes have proper markdown format
- Try rebuilding index:
  ```bash
  python tools/index_vault.py --rebuild
  ```

### Platform-Specific Issues

#### Windows

**PowerShell Execution Policy:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Long Path Support:**
```powershell
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

#### macOS

**Command Line Tools:**
```bash
xcode-select --install
```

**Rosetta 2 (Apple Silicon):**
```bash
# If needed for x86_64 dependencies
softwareupdate --install-rosetta
```

#### Linux

**Build Dependencies:**
```bash
sudo apt-get install python3-dev build-essential
```

**Virtual Environment Issues:**
```bash
sudo apt-get install python3-venv
```

## Advanced Configuration

### Custom Index Settings

Edit `00 - System/.agent/tools/index_vault.py`:

```python
# Adjust chunk size for longer passages
CHUNK_SIZE = 1000  # Default: 500

# Adjust overlap for better context
CHUNK_OVERLAP = 200  # Default: 100

# Exclude certain directories
EXCLUDE_DIRS = ['99 - Archive', 'temp']
```

### GPU Acceleration (Optional)

For faster embeddings with CUDA GPU:

```bash
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118
pip uninstall faiss-cpu
pip install faiss-gpu
```

Edit indexing scripts to use GPU device:
```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
```

### Logging Configuration

Edit `00 - System/.agent/tools/config.py`:

```python
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "logs/session_log.jsonl"
```

## Updating

### Update Python Dependencies

```bash
cd "00 - System/.agent"
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install --upgrade -r requirements.txt
```

### Rebuild FAISS Index

After adding many new notes:

```bash
python tools/index_vault.py --rebuild
```

### Update from Git

```bash
git pull origin main
cd "00 - System/.agent"
pip install -r requirements.txt --upgrade
python tools/index_vault.py --rebuild
```

## Next Steps

1. **Read the Documentation**
   - [Vault Constitution](00%20-%20System/Vault%20Constitution.md)
   - [Study Agent Architecture](00%20-%20System/Study%20Agent%20Architecture.md)

2. **Create Your First Note**
   ```bash
   python tools/create_note.py --type concept --title "Photosynthesis" --subject Biology
   ```

3. **Start Learning**
   - Open Obsidian
   - Navigate to `01 - Inbox`
   - Create a note with your study question
   - Let the agents guide you!

4. **Customize Templates**
   - Edit templates in `08 - Templates/`
   - Adjust to your learning style
   - Add subject-specific sections

## Getting Help

- **Setup Issues:** Open issue on GitHub with setup log
- **Usage Questions:** Check [README.md](README.md) and documentation
- **Feature Requests:** See [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Installation Time:** ~5-10 minutes  
**Disk Space Required:** ~2GB (including models and dependencies)  
**Internet Required:** Initial setup only (after that, works offline except web research)
