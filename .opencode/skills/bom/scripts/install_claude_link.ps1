<#
.SYNOPSIS
    Link (default) or copy the BOM skill into the Claude skills directory.

.DESCRIPTION
    Creates a directory junction (no admin rights required) so that editing this
    repository is immediately visible to the agent. Use -Copy if junctions are
    not allowed by policy.

.EXAMPLE
    pwsh -File install_claude_link.ps1
    pwsh -File install_claude_link.ps1 -Target "$HOME\.config\opencode\skills\bom"
    pwsh -File install_claude_link.ps1 -Copy -Force
#>
[CmdletBinding()]
param(
    [string]$Source = (Split-Path -Parent (Split-Path -Parent $PSCommandPath)),
    [string]$Target = (Join-Path $HOME ".claude\skills\bom"),
    [switch]$Copy,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $Source "SKILL.md"))) {
    throw "SKILL.md introuvable dans '$Source'. Le script doit rester dans scripts/."
}

$parent = Split-Path -Parent $Target
if (-not (Test-Path $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Write-Host "dossier cree : $parent"
}

if (Test-Path $Target) {
    $item = Get-Item $Target -Force
    $isLink = $item.Attributes -band [IO.FileAttributes]::ReparsePoint
    if ($isLink -or $Copy) {
        if (-not $Force) {
            throw "'$Target' existe deja. Relancer avec -Force pour le remplacer."
        }
        if ($isLink) {
            # remove the link only, never the target content
            [IO.Directory]::Delete($Target, $false)
        } else {
            Remove-Item -Recurse -Force $Target
        }
        Write-Host "existant remplace"
    } else {
        throw "'$Target' existe et n'est pas un lien. Deplacer ou supprimer manuellement."
    }
}

if ($Copy) {
    Copy-Item -Path $Source -Destination $Target -Recurse -Force
    Write-Host "copie   : $Source -> $Target"
} else {
    New-Item -ItemType Junction -Path $Target -Target (Resolve-Path $Source) | Out-Null
    Write-Host "junction: $Source -> $Target"
}

$entry = Join-Path $Target "scripts\bom.py"
if (Test-Path $entry) {
    $version = & python $entry --version 2>&1
    Write-Host "verification : $version"
    Write-Host "PASS. Relancer une session pour que le skill soit charge."
} else {
    Write-Warning "bom.py non trouve dans la cible."
}
