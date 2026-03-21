#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Wrapper script for create_note.py that accepts content via parameter and pipes to stdin
    
.DESCRIPTION
    This script accepts note content via -Content parameter, then pipes it to create_note.py
    via stdin, solving the PowerShell command-line length limit issue for large notes.
    The parameter is received by PowerShell, but then piped to Python via stdin internally.
    
.PARAMETER VaultPath
    Path to the Obsidian vault
    
.PARAMETER Title
    Title of the note
    
.PARAMETER Content
    Note content (markdown with YAML frontmatter)
    
.PARAMETER Folder
    Subfolder within vault (optional, e.g., "04 - Concepts")
    
.PARAMETER FilenameTemplate
    Filename template (default: {title}.md)
    
.EXAMPLE
    .\create_note_stdin.ps1 -VaultPath "C:\vault" -Title "My Note" -Content "# Content" -Folder "04 - Concepts"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$VaultPath,
    
    [Parameter(Mandatory=$true)]
    [string]$Title,
    
    [Parameter(Mandatory=$true, ValueFromPipeline=$true)]
    [string]$Content,
    
    [Parameter(Mandatory=$false)]
    [string]$Folder = "",
    
    [Parameter(Mandatory=$false)]
    [string]$FilenameTemplate = "{title}.md"
)

process {
    # Ensure PowerShell pipes Unicode strings as UTF-8 bytes (without BOM) to Python stdin
    $OutputEncoding = New-Object System.Text.UTF8Encoding $false

    if ([string]::IsNullOrWhiteSpace($Content)) {
        $errorResult = @{
            success = $false
            error = "No content provided"
        } | ConvertTo-Json -Compress
        Write-Output $errorResult
        exit 1
    }
    
    $agentDir   = Split-Path -Parent $PSScriptRoot
    $pythonPath = Join-Path $agentDir "venv\Scripts\python.exe"
    $scriptPath = Join-Path $PSScriptRoot "create_note.py"
    $indexScript = Join-Path $PSScriptRoot "index_vault.py"
    
    # Build arguments
    $args = @(
        $scriptPath,
        $VaultPath,
        $Title,
        "--stdin",
        "--filename-template", $FilenameTemplate
    )
    
    if (![string]::IsNullOrWhiteSpace($Folder)) {
        $args += "--folder", $Folder
    }
    
    # Pipe content to Python script via stdin (this is the key - we receive via param, pipe to python)
    try {
        $result = $Content | & $pythonPath @args 2>&1
        
        # Check if result is valid JSON
        try {
            $parsed = $result | ConvertFrom-Json
            
            # --- IndexerAgent: auto-reindex after successful note creation ---
            if ($parsed.success -eq $true) {
                $indexStart = [System.Diagnostics.Stopwatch]::StartNew()
                $null = & $pythonPath $indexScript 2>&1
                $indexStart.Stop()
                $indexedOk = ($LASTEXITCODE -eq 0)
                
                # Enrich result JSON with indexing metadata
                $enriched = @{
                    success        = $parsed.success
                    path           = $parsed.path
                    indexed        = $indexedOk
                    index_time_ms  = [int]$indexStart.Elapsed.TotalMilliseconds
                } | ConvertTo-Json -Compress
                Write-Output $enriched
            } else {
                Write-Output $result
            }
        } catch {
            # Not valid JSON, wrap error
            $errorResult = @{
                success = $false
                error = "Python script error: $result"
            } | ConvertTo-Json -Compress
            Write-Output $errorResult
            exit 1
        }
    } catch {
        $errorResult = @{
            success = $false
            error = $_.Exception.Message
        } | ConvertTo-Json -Compress
        Write-Output $errorResult
        exit 1
    }
}
