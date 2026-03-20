<#
.SYNOPSIS
    One-shot setup for the Research Agent vault after cloning.

.DESCRIPTION
    Checks prerequisites, creates Python venv, installs dependencies,
    configures TAVILY_API_KEY, indexes the vault, and verifies the
    installation. All paths are derived from the script location —
    no hardcoded paths. Works wherever the repo is cloned or copied.

.EXAMPLE
    # From the vault root:
    & ".\00 - System\.agent\setup_windows.ps1"

    # Or from the agent directory:
    .\setup_windows.ps1
#>
#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths (all relative to script location — never hardcoded) ─────────────────
$agentDir  = $PSScriptRoot
$vaultRoot = (Get-Item (Join-Path $agentDir "..\..")).FullName
$toolsDir  = Join-Path $agentDir "tools"
$venvDir   = Join-Path $agentDir "venv"
$modelDir  = Join-Path $agentDir "models\all-MiniLM-L6-v2"
$faissDir  = Join-Path $agentDir "faiss_store"
$python    = Join-Path $venvDir "Scripts\python.exe"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Step { param([string]$msg) Write-Host "`n▶  $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "  ✅  $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "  ⚠️   $msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$msg) Write-Host "`n  ❌  $msg`n" -ForegroundColor Red; exit 1 }

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   Research Agent Vault — Windows Setup                    " -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Vault root : $vaultRoot"
Write-Host "  Agent dir  : $agentDir"
Write-Host ""

# ── Step 1: Check Python ──────────────────────────────────────────────────────
Write-Step "Checking Python..."
try {
    $pyVersion = & python --version 2>&1
    if ($pyVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]; $minor = [int]$Matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 14)) {
            Write-Fail "Python 3.14+ required. Found: $pyVersion. Download from https://python.org/downloads/"
        }
        Write-OK "$pyVersion detected"
    } else {
        Write-Fail "Could not parse Python version. Ensure Python is in PATH."
    }
} catch {
    Write-Fail "Python not found. Install from https://python.org/downloads/ and add to PATH."
}

# ── Step 2: Extract embedding model from zip ─────────────────────────────────
Write-Step "Checking embedding model..."
$modelZip = Join-Path $agentDir "models\all-miniLM-L6-v2.zip"

$modelPresent = (Test-Path (Join-Path $modelDir "pytorch_model.bin")) -or
                (Test-Path (Join-Path $modelDir "model.safetensors"))

if ($modelPresent) {
    Write-OK "Embedding model already present at: $modelDir"
} elseif (Test-Path $modelZip) {
    Write-Host "  Extracting model from zip..." -ForegroundColor Yellow
    try {
        Expand-Archive -Path $modelZip -DestinationPath (Join-Path $agentDir "models") -Force
        # Zip extracts as 'all-MiniLM-L6-v2.pt' — rename to expected folder name
        $extractedDir = Join-Path $agentDir "models\all-MiniLM-L6-v2.pt"
        if ((Test-Path $extractedDir) -and -not (Test-Path $modelDir)) {
            Rename-Item -Path $extractedDir -NewName "all-MiniLM-L6-v2"
        }
        $modelPresent = (Test-Path (Join-Path $modelDir "pytorch_model.bin")) -or
                        (Test-Path (Join-Path $modelDir "model.safetensors"))
        if ($modelPresent) {
            Write-OK "Embedding model extracted to: $modelDir"
        } else {
            Write-Warn "Extraction completed but model files not found — check zip contents."
        }
    } catch {
        Write-Fail "Failed to extract model zip: $_"
    }
} else {
    Write-Warn "Model zip not found at: $modelZip"
    Write-Warn "Ensure 'all-miniLM-L6-v2.zip' is present in the models folder, then re-run."
}

# ── Step 3: Create virtual environment ────────────────────────────────────────
Write-Step "Creating Python virtual environment..."
if (Test-Path $python) {
    Write-OK "venv already exists — skipping creation"
} else {
    & python -m venv $venvDir
    if (-not (Test-Path $python)) {
        Write-Fail "venv creation failed. Verify Python installation."
    }
    Write-OK "venv created at: $venvDir"
}

# ── Step 4: Install dependencies ──────────────────────────────────────────────
Write-Step "Installing Python dependencies (this may take a few minutes)..."
$requirements = Join-Path $toolsDir "requirements.txt"
if (-not (Test-Path $requirements)) {
    Write-Fail "requirements.txt not found at: $requirements"
}

& $python -m pip install --quiet --upgrade pip
& $python -m pip install --quiet -r $requirements
if ($LASTEXITCODE -ne 0) {
    Write-Fail "pip install failed. Check requirements.txt and your network connection."
}
Write-OK "All dependencies installed"

# ── Step 4b: Convert pytorch_model.bin → model.safetensors ──────────────────
# PyTorch 2.6+ sets weights_only=True by default, which blocks .bin (pickle)
# loading. sentence-transformers prefers .safetensors when present.
Write-Step "Checking model format (PyTorch 2.6+ safetensors requirement)..."
$binPath        = Join-Path $modelDir "pytorch_model.bin"
$safetensorsPath = Join-Path $modelDir "model.safetensors"
if ((Test-Path $binPath) -and -not (Test-Path $safetensorsPath)) {
    Write-Host "  Converting pytorch_model.bin → model.safetensors..." -ForegroundColor Yellow
    $convertScript = @"
import sys, os
import torch
from safetensors.torch import save_file

bin_path = sys.argv[1]
out_path = sys.argv[2]
state_dict = torch.load(bin_path, map_location="cpu", weights_only=False)
save_file(state_dict, out_path)
print("OK")
"@
    $tmpScript = Join-Path $env:TEMP "convert_model.py"
    $convertScript | Set-Content -Path $tmpScript -Encoding UTF8
    $result = & $python $tmpScript $binPath $safetensorsPath 2>&1
    Remove-Item $tmpScript -ErrorAction SilentlyContinue
    if ((Test-Path $safetensorsPath) -and ($result -match "OK")) {
        Write-OK "model.safetensors created — future loads use safe format"
    } else {
        Write-Warn "Conversion failed: $result"
        Write-Warn "Indexing may fail. Try: pip install --upgrade torch safetensors"
    }
} elseif (Test-Path $safetensorsPath) {
    Write-OK "model.safetensors already present — no conversion needed"
} else {
    Write-Warn "No model files found — skipping conversion (see Step 2)"
}

# ── Step 5: Configure TAVILY_API_KEY ─────────────────────────────────────────
Write-Step "Configuring Tavily API key (required for web research)..."
$existingKey = [System.Environment]::GetEnvironmentVariable("TAVILY_API_KEY", "User")
if ($existingKey -and $existingKey -match "^tvly-") {
    Write-OK "TAVILY_API_KEY already set in Windows user environment"
} else {
    Write-Host ""
    Write-Host "  Get a free key at: https://tavily.com" -ForegroundColor White
    Write-Host "  Press ENTER to skip (web research will be disabled until key is set)" -ForegroundColor Gray
    $apiKey = Read-Host "  Enter your Tavily API key (tvly-...)"
    $apiKey = $apiKey.Trim()
    if ($apiKey -match "^tvly-") {
        [System.Environment]::SetEnvironmentVariable("TAVILY_API_KEY", $apiKey, "User")
        $env:TAVILY_API_KEY = $apiKey
        Write-OK "TAVILY_API_KEY saved to Windows user environment (persists across sessions)"
    } elseif ($apiKey -ne "") {
        Write-Warn "Key format unexpected (expected 'tvly-...'). Not saved."
        Write-Warn "Set manually later: [System.Environment]::SetEnvironmentVariable('TAVILY_API_KEY','tvly-...','User')"
    } else {
        Write-Warn "Skipped. Web research will be disabled until TAVILY_API_KEY is configured."
        Write-Warn "Set later: [System.Environment]::SetEnvironmentVariable('TAVILY_API_KEY','tvly-...','User')"
    }
}

# ── Step 6: Index the vault ───────────────────────────────────────────────────
Write-Step "Building FAISS semantic search index..."
if (-not $modelPresent) {
    Write-Warn "Skipping index — embedding model not found (see Step 2)."
    Write-Warn "After installing the model, re-index with:"
    Write-Warn "  & `"$python`" `"$toolsDir\index_vault.py`" `"$vaultRoot`" `"$faissDir`" `"$modelDir`""
} else {
    & $python "$toolsDir\index_vault.py" "$vaultRoot" "$faissDir" "$modelDir"
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Vault indexed successfully"
    } else {
        Write-Warn "Indexing returned a non-zero exit code — check output above."
    }
}

# ── Step 7: Verify installation ───────────────────────────────────────────────
Write-Step "Verifying installation with a test query..."
$indexFile = Join-Path $faissDir "index.faiss"
if ($modelPresent -and (Test-Path $indexFile)) {
    $testResult = & $python "$toolsDir\query_vault.py" "vault constitution" "$faissDir" "$modelDir" 1 2>&1
    if ($testResult -match '"file_path"') {
        Write-OK "Semantic search working — vault is queryable"
    } else {
        Write-Warn "Test query returned unexpected output. Index may be empty (no markdown files committed yet)."
    }
} else {
    Write-Warn "Skipping verification — index not present."
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "   Setup complete!                                         " -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Run the research agent:" -ForegroundColor White
Write-Host "    copilot agent run `"$vaultRoot\00 - System\research.agent.md`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Run the maintenance agent:" -ForegroundColor White
Write-Host "    copilot agent run `"$vaultRoot\00 - System\maintenance.agent.md`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Re-index vault after adding notes:" -ForegroundColor White
Write-Host "    & `"$python`" `"$toolsDir\index_vault.py`" `"$vaultRoot`" `"$faissDir`" `"$modelDir`"" -ForegroundColor Yellow
Write-Host ""
