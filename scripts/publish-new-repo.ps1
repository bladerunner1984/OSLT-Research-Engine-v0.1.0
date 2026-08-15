param(
    [string]$Owner = "bladerunner1984",
    [string]$Repository = "oslt-research-engine"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI is required. Install it with: winget install --id GitHub.cli"
}

gh auth status
python scripts\preflight.py
pytest

if (-not (Test-Path .git)) {
    git init -b main
}

if (-not (git config user.name)) {
    throw "Set git identity first: git config --global user.name 'Mark Jennings'"
}
if (-not (git config user.email)) {
    throw "Set git identity first: git config --global user.email 'YOUR_GITHUB_EMAIL'"
}

git add --all
if (-not (git diff --cached --quiet)) {
    git commit -m "bootstrap governed OSLT research engine"
}

$FullName = "$Owner/$Repository"
$Exists = $true
try {
    gh repo view $FullName --json nameWithOwner | Out-Null
} catch {
    $Exists = $false
}

if (-not $Exists) {
    gh repo create $FullName --private --source . --remote origin --push `
        --description "Governed multidisciplinary research engine and Pilot 1 public-evidence platform"
} else {
    if (-not (git remote get-url origin 2>$null)) {
        git remote add origin "https://github.com/$FullName.git"
    }
    git push -u origin main
}

# Attempt fail-closed branch protection. Some account plans may require configuring this in the UI.
$Protection = @{
    required_status_checks = @{
        strict = $true
        contexts = @("ci / check")
    }
    enforce_admins = $true
    required_pull_request_reviews = $null
    restrictions = $null
    required_linear_history = $false
    allow_force_pushes = $false
    allow_deletions = $false
} | ConvertTo-Json -Depth 5

$ProtectionFile = Join-Path $env:TEMP "oslt-branch-protection.json"
Set-Content -Path $ProtectionFile -Value $Protection -Encoding utf8
try {
    gh api --method PUT "repos/$FullName/branches/main/protection" --input $ProtectionFile | Out-Null
    Write-Host "Branch protection configured: requires ci / check." -ForegroundColor Green
} catch {
    Write-Warning "Repository was created and pushed, but branch protection must be configured manually."
}

Write-Host "Published https://github.com/$FullName" -ForegroundColor Green
