$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.12 or newer is required."
}

python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts\generate_reference_manifest.py
python scripts\export_schemas.py
python scripts\preflight.py
pytest
Write-Host "OSLT local bootstrap complete." -ForegroundColor Green
