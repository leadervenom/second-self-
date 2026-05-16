$ErrorActionPreference = "Stop"

Write-Host "== Second Self Windows setup =="

if (!(Test-Path "package.json")) {
  throw "Run this script from the project root folder that contains package.json."
}

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python not found. Install Python 3.11 or 3.12, then reopen PowerShell."
}

if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm not found. Install Node.js LTS, then reopen PowerShell."
}

if (!(Test-Path ".venv")) {
  python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements-windows.txt

if (!(Test-Path ".env")) {
  Copy-Item ".env.windows.demo" ".env"
  Write-Host "Created .env from .env.windows.demo"
} else {
  Write-Host ".env already exists; leaving it unchanged."
}

npm ci

Write-Host "Setup complete. Open two PowerShell windows:"
Write-Host "1) .\start-backend.ps1"
Write-Host "2) .\start-frontend.ps1"
