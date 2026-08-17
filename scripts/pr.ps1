# Crea un PR: pushea la rama actual y abre la URL de GitHub.
# Equivalente al target `make pr` para Windows.

[CmdletBinding()]
param(
    [string]$Remote = "origin"
)

$ErrorActionPreference = "Stop"

$branch = git rev-parse --abbrev-ref HEAD
if ($LASTEXITCODE -ne 0) {
    Write-Error "No se pudo determinar la rama actual."
    exit 1
}

Write-Host ">> pusheando rama $branch..."
git push -u $Remote $branch
if ($LASTEXITCODE -ne 0) {
    Write-Error "Fallo el push."
    exit 1
}

$remoteUrl = git remote get-url $Remote
$repo = [regex]::Replace($remoteUrl, '.*github.com[:/](.*?)(\.git)?$', '$1')

$url = "https://github.com/$repo/pull/new/$branch"
Write-Host ">> abriendo $url"
Start-Process $url