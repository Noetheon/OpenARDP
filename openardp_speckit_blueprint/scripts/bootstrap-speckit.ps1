$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
$Version = (Get-Content "spec-kit/PINNED_VERSION.txt" -Raw).Trim()

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv first, then rerun this script."
}

if (Get-Command git -ErrorAction SilentlyContinue) {
    try {
        git rev-parse --is-inside-work-tree *> $null
        if ($LASTEXITCODE -eq 0) {
            git diff --quiet
            $WorktreeClean = ($LASTEXITCODE -eq 0)
            git diff --cached --quiet
            $IndexClean = ($LASTEXITCODE -eq 0)
            if (-not ($WorktreeClean -and $IndexClean)) {
                Write-Warning "The Git working tree has changes. Commit or back them up before continuing."
            }
        }
    } catch {
        Write-Warning "Could not inspect Git state."
    }
} else {
    Write-Warning "Initialize and commit a Git repository before implementation for full traceability."
}

Write-Host "Installing GitHub Spec Kit specify-cli==$Version ..."
uv tool install "specify-cli==$Version" --force

Write-Host "Initializing Spec Kit for Codex in the existing repository ..."
specify init --here --force --integration codex --ignore-agent-tools

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command py -ErrorAction SilentlyContinue
    if ($Python) {
        & $Python.Source -3 scripts/apply-speckit-overlay.py
    } else {
        throw "Python 3 is required to apply the OpenARDP overlay."
    }
} else {
    & $Python.Source scripts/apply-speckit-overlay.py
}

Write-Host "`nSpec Kit version:"
specify version

Write-Host "`nIntegration status:"
specify integration status
if ($LASTEXITCODE -ne 0) {
    throw "Spec Kit reported an integration error. Review the output before using Codex."
}

Write-Host "`nBootstrap complete."
Write-Host "Next: open Codex in this repository and paste spec-kit/FIRST_CODEX_SESSION.md."
