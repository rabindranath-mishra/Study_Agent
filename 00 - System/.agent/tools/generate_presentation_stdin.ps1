#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Wrapper for generate_presentation.py — accepts markdown content via stdin or source file path.

.PARAMETER VaultPath
    Path to the Obsidian vault root.

.PARAMETER Source
    Path to source markdown file (relative to vault root), or '-' for stdin.

.PARAMETER Content
    Markdown content (used when Source is '-').

.PARAMETER Title
    Override presentation title.

.PARAMETER OutputDir
    Output directory (default: 07 - Writing/presentations).

.EXAMPLE
    .\generate_presentation_stdin.ps1 -Source "03 - Research\MRI Patient Preparation AI System Architecture.md"
    .\generate_presentation_stdin.ps1 -Source "-" -Content $markdownText -Title "My Talk"
    .\generate_presentation_stdin.ps1 -VaultPath "D:\my-vault" -Source "03 - Research\MyNote.md"
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$VaultPath = "",

    [Parameter(Mandatory=$true)]
    [string]$Source,

    [Parameter(Mandatory=$false)]
    [string]$Content = "",

    [Parameter(Mandatory=$false)]
    [string]$Title = "",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = ""
)

$agentDir   = Split-Path -Parent $PSScriptRoot
$vaultRoot  = Split-Path -Parent (Split-Path -Parent $agentDir)
if ([string]::IsNullOrEmpty($VaultPath)) { $VaultPath = $vaultRoot }
$pythonPath = Join-Path $agentDir "venv\Scripts\python.exe"
$scriptPath = Join-Path $PSScriptRoot "generate_presentation.py"

$argList = @(
    $scriptPath,
    "--source",     $Source,
    "--vault-path", $VaultPath
)

if ($Title)     { $argList += "--title",      $Title }
if ($OutputDir) { $argList += "--output-dir", $OutputDir }

try {
    if ($Source -eq "-") {
        if ([string]::IsNullOrWhiteSpace($Content)) {
            Write-Output '{"success":false,"error":"Source is stdin but no Content provided"}'
            exit 1
        }
        $result = $Content | & $pythonPath @argList 2>&1
    } else {
        $result = & $pythonPath @argList 2>&1
    }

    # Validate JSON and pass through
    try {
        $parsed = $result | ConvertFrom-Json
        Write-Output ($parsed | ConvertTo-Json -Compress)
    } catch {
        Write-Output ((@{ success = $false; error = "Tool output: $result" }) | ConvertTo-Json -Compress)
        exit 1
    }
} catch {
    Write-Output ((@{ success = $false; error = $_.Exception.Message }) | ConvertTo-Json -Compress)
    exit 1
}
