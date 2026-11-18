<#
.SYNOPSIS
    One-shot setup for the Study Agent vault after cloning.

.DESCRIPTION
    Checks prerequisites, verifies the vault skeleton, creates the Python
    virtual environment, installs dependencies, configures API keys, builds
    the FAISS semantic index, and verifies the installation.

    All paths are derived from the script location, so the vault can be
    cloned or moved anywhere.

.PARAMETER SkipIndex
    Do not build the FAISS index (useful when the embedding model is missing).

.PARAMETER Reindex
    Force a full index rebuild even when an index already exists.

.PARAMETER SkipTests
    Skip the pytest run at the end of setup.

.PARAMETER NonInteractive
    Never prompt for API keys. Missing keys are reported as warnings.

.EXAMPLE
    # From the vault root:
    & ".\00 - System\.agent\setup_windows.ps1"

.EXAMPLE
    # Rebuild the index and skip the test run:
    & ".\00 - System\.agent\setup_windows.ps1" -Reindex -SkipTests
#>
#Requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$SkipIndex,
    [switch]$Reindex,
    [switch]$SkipTests,
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths (all relative to script location — never hardcoded) ─────────────────
$agentDir  = $PSScriptRoot
$vaultRoot = (Get-Item (Join-Path $agentDir "..\..")).FullName
$toolsDir  = Join-Path $agentDir "tools"
$venvDir   = Join-Path $agentDir "venv"
$modelDir  = Join-Path $agentDir "models\all-MiniLM-L6-v2"
$modelZip  = Join-Path $agentDir "models\all-miniLM-L6-v2.zip"
$faissDir  = Join-Path $agentDir "faiss_store"
$python    = Join-Path $venvDir "Scripts\python.exe"
$envFile   = Join-Path $vaultRoot ".env"
$agentFile = Join-Path $vaultRoot "00 - System\study.agent.md"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Step { param([string]$msg) Write-Host "`n▶  $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "  ✅  $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "  ⚠️   $msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$msg) Write-Host "`n  ❌  $msg`n" -ForegroundColor Red; exit 1 }

function Set-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )
    $lines = New-Object System.Collections.Generic.List[string]
    if (Test-Path $Path) {
        foreach ($line in (Get-Content -Path $Path)) { $lines.Add($line) }
    }
    $pattern = "^\s*" + [regex]::Escape($Key) + "\s*="
    $replaced = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = "$Key=$Value"
            $replaced = $true
        }
    }
    if (-not $replaced) { $lines.Add("$Key=$Value") }
    # Write without a BOM so Node's loadEnvFile reads the first key correctly.
    [System.IO.File]::WriteAllLines($Path, $lines, (New-Object System.Text.UTF8Encoding($false)))
}

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key
    )
    if (-not (Test-Path $Path)) { return $null }
    $pattern = "^\s*" + [regex]::Escape($Key) + "\s*=(.*)$"
    foreach ($line in (Get-Content -Path $Path)) {
        if ($line -match $pattern) {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   Study Agent Vault — Windows Setup                       " -ForegroundColor Cyan
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

# ── Step 2: Verify vault skeleton and agent definition ────────────────────────
Write-Step "Verifying vault skeleton..."
$requiredDirs = @(
    "00 - System", "01 - Inbox", "02 - Sources", "03 - Subjects",
    "04 - Concepts", "05 - Practice", "06 - Plans", "07 - Outputs",
    "08 - Templates", "99 - Archive"
)
$createdDirs = @()
foreach ($dir in $requiredDirs) {
    $path = Join-Path $vaultRoot $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
        $createdDirs += $dir
    }
}
if ($createdDirs.Count -gt 0) {
    Write-Warn "Created missing folder(s): $($createdDirs -join ', ')"
} else {
    Write-OK "All 10 vault folders present"
}

if (-not (Test-Path $agentFile)) {
    Write-Fail "study.agent.md not found at: $agentFile"
}
Write-OK "Agent definition found: 00 - System\study.agent.md"

# ── Step 3: Extract embedding model from zip ─────────────────────────────────
Write-Step "Checking embedding model..."
$modelPresent = (Test-Path (Join-Path $modelDir "pytorch_model.bin")) -or
                (Test-Path (Join-Path $modelDir "model.safetensors"))

if ($modelPresent) {
    Write-OK "Embedding model already present at: $modelDir"
} elseif (Test-Path $modelZip) {
    Write-Host "  Extracting model from zip..." -ForegroundColor Yellow
    try {
        Expand-Archive -Path $modelZip -DestinationPath (Join-Path $agentDir "models") -Force
        # The zip extracts as 'all-MiniLM-L6-v2.pt' — rename to the expected folder name.
        $extractedDir = Join-Path $agentDir "models\all-MiniLM-L6-v2.pt"
        if ((Test-Path $extractedDir) -and -not $modelPresent) {
            if (Test-Path $modelDir) { Remove-Item -Path $modelDir -Recurse -Force }
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
    Write-Warn "Place 'all-miniLM-L6-v2.zip' in the models folder, then re-run setup."
}

# ── Step 4: Create virtual environment ────────────────────────────────────────
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

# ── Step 5: Install dependencies ──────────────────────────────────────────────
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

# pytest is a development dependency used by the verification step.
& $python -m pip install --quiet pytest
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Could not install pytest — the test step will be skipped."
}
Write-OK "All dependencies installed"

# ── Step 5b: Convert pytorch_model.bin → model.safetensors ──────────────────
# PyTorch 2.6+ sets weights_only=True by default, which blocks .bin (pickle)
# loading. sentence-transformers prefers .safetensors when present.
Write-Step "Checking model format (PyTorch 2.6+ safetensors requirement)..."
$binPath         = Join-Path $modelDir "pytorch_model.bin"
$safetensorsPath = Join-Path $modelDir "model.safetensors"
if ((Test-Path $binPath) -and -not (Test-Path $safetensorsPath)) {
    Write-Host "  Converting pytorch_model.bin → model.safetensors..." -ForegroundColor Yellow
    $convertScript = @"
import sys
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
    Write-Warn "No model files found — skipping conversion (see Step 3)"
}

# ── Step 6: Configure TAVILY_API_KEY (web research) ──────────────────────────
Write-Step "Configuring Tavily API key (optional — enables web research)..."
$existingTavily = [System.Environment]::GetEnvironmentVariable("TAVILY_API_KEY", "User")
if ($existingTavily -and $existingTavily -match "^tvly-") {
    Write-OK "TAVILY_API_KEY already set in Windows user environment"
} elseif ($NonInteractive) {
    Write-Warn "TAVILY_API_KEY not set — web research will be disabled."
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
    }
}

# ── Step 7: Configure SARVAM_API_KEY (sarvam-chat.mjs) ───────────────────────
Write-Step "Configuring Sarvam API key (used by sarvam-chat.mjs)..."
$sarvamKey = $env:SARVAM_API_KEY
if (-not $sarvamKey) { $sarvamKey = Get-DotEnvValue -Path $envFile -Key "SARVAM_API_KEY" }

if ($sarvamKey) {
    Write-OK "SARVAM_API_KEY is configured"
} elseif ($NonInteractive) {
    Write-Warn "SARVAM_API_KEY not set — sarvam-chat.mjs will fail until it is."
} else {
    Write-Host ""
    Write-Host "  Press ENTER to skip (only sarvam-chat.mjs needs this key)" -ForegroundColor Gray
    $sarvamInput = Read-Host "  Enter your Sarvam API key"
    $sarvamInput = $sarvamInput.Trim()
    if ($sarvamInput -ne "") {
        Set-DotEnvValue -Path $envFile -Key "SARVAM_API_KEY" -Value $sarvamInput
        $env:SARVAM_API_KEY = $sarvamInput
        Write-OK "SARVAM_API_KEY written to $envFile (gitignored)"
    } else {
        Write-Warn "Skipped. sarvam-chat.mjs will fail until SARVAM_API_KEY is set in .env."
    }
}

Write-Step "Checking Node.js (required only by sarvam-chat.mjs)..."
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) {
    $nodeVersion = & node --version
    Write-OK "Node.js $nodeVersion detected"
    $npmRoot = & npm root -g 2>$null
    if ($npmRoot -and (Test-Path (Join-Path $npmRoot "sarvamai"))) {
        Write-OK "sarvamai SDK found in global npm modules"
    } else {
        Write-Warn "sarvamai not installed globally. Run: npm install -g sarvamai"
    }
} else {
    Write-Warn "Node.js not found — sarvam-chat.mjs will not run (vault tools are unaffected)."
}

# ── Step 8: Build the FAISS index ─────────────────────────────────────────────
Write-Step "Building FAISS semantic search index..."
$indexFile = Join-Path $faissDir "index.faiss"
if ($SkipIndex) {
    Write-Warn "Skipped (-SkipIndex)."
} elseif (-not $modelPresent) {
    Write-Warn "Skipping index — embedding model not found (see Step 3)."
} elseif ((Test-Path $indexFile) -and -not $Reindex) {
    Write-OK "Index already present — use -Reindex to rebuild."
} else {
    & $python "$toolsDir\index_vault.py" --rebuild
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Vault indexed successfully"
    } else {
        Write-Warn "Indexing returned exit code $LASTEXITCODE — check output above."
    }
}

# ── Step 9: Verify installation ───────────────────────────────────────────────
Write-Step "Verifying installation with a test query..."
if ($modelPresent -and (Test-Path $indexFile)) {
    $testResult = & $python "$toolsDir\query_vault.py" "vault constitution" 1 2>$null
    $testText = ($testResult -join "`n")
    if ($LASTEXITCODE -eq 0 -and $testText -match '"score"') {
        Write-OK "Semantic search working — vault is queryable"
    } else {
        Write-Warn "Test query returned unexpected output. Re-run with -Reindex."
    }
} else {
    Write-Warn "Skipping verification — index not present."
}

# ── Step 10: Run the test suite ───────────────────────────────────────────────
Write-Step "Running the test suite..."
if ($SkipTests) {
    Write-Warn "Skipped (-SkipTests)."
} elseif (-not (Test-Path $indexFile)) {
    Write-Warn "Skipping tests — the FAISS index is required by the suite."
} else {
    & $python -m pytest "$agentDir\tests" -q --no-header
    if ($LASTEXITCODE -eq 0) {
        Write-OK "All tests passed"
    } else {
        Write-Warn "Some tests failed — review the output above."
    }
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "   Setup complete!                                         " -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Run the study agent:" -ForegroundColor White
Write-Host "    copilot agent run `"$vaultRoot\00 - System\study.agent.md`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Or open the vault in Obsidian and use the Copilot ACP Agent panel." -ForegroundColor White
Write-Host "  Plugin settings: Settings → Copilot ACP Agent" -ForegroundColor Gray
Write-Host "    copilotPath : <path to copilot.cmd>"
Write-Host "    vaultPath   : $vaultRoot"
Write-Host "    promptPresetsText : study.agent.md"
Write-Host ""
Write-Host "  Re-index the vault after adding notes:" -ForegroundColor White
Write-Host "    & `"$python`" `"$toolsDir\index_vault.py`" --rebuild" -ForegroundColor Yellow
Write-Host ""
