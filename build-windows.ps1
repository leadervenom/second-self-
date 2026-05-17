$ErrorActionPreference = "Stop"

Write-Host "== Building S.A.I Windows Desktop App =="

if (!(Test-Path "package.json")) {
  throw "Run this script from the project root folder that contains package.json."
}

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python not found. Install Python 3.11 or 3.12, then reopen PowerShell."
}

if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm not found. Install Node.js LTS, then reopen PowerShell."
}

Write-Host "Closing old S.A.I/Electron/Node/Python processes if running..."

taskkill /IM "S.A.I.exe" /F 2>$null
taskkill /IM "electron.exe" /F 2>$null
taskkill /IM "sai-backend.exe" /F 2>$null
taskkill /IM "node.exe" /F 2>$null

Write-Host "Checking ports 3000 and 8000..."

$ports = @(3000, 8000)

foreach ($port in $ports) {
  $lines = netstat -ano | Select-String ":$port" | Select-String "LISTENING"

  foreach ($line in $lines) {
    $parts = ($line.ToString() -split "\s+") | Where-Object { $_ -ne "" }
    $pid = $parts[-1]

    if ($pid -match "^\d+$") {
      Write-Host "Killing process on port $port with PID $pid"
      taskkill /PID $pid /F 2>$null
    }
  }
}

Start-Sleep -Seconds 2

if (!(Test-Path ".env")) {
  if (Test-Path ".env.example") {
    Copy-Item ".env.example" ".env"
    throw "Created .env from .env.example. Fill in your Gemini API key, then run this script again."
  } elseif (Test-Path ".env.windows.demo") {
    Copy-Item ".env.windows.demo" ".env"
    throw "Created .env from .env.windows.demo. Fill in your Gemini API key, then run this script again."
  } else {
    throw ".env is missing. Create one before building."
  }
}

if (!(Test-Path ".venv")) {
  python -m venv .venv
}

Write-Host "Installing Python dependencies..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip

if (Test-Path "requirements-windows.txt") {
  & .\.venv\Scripts\pip.exe install -r requirements-windows.txt
} else {
  & .\.venv\Scripts\pip.exe install -r requirements.txt
}

& .\.venv\Scripts\pip.exe install pyinstaller

Write-Host "Installing Node dependencies..."
npm ci

Write-Host "Building backend executable..."
Remove-Item -Recurse -Force .\dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\build -ErrorAction SilentlyContinue
& .\.venv\Scripts\pyinstaller.exe --onefile --name sai-backend backend_launcher.py

if (!(Test-Path ".\dist\sai-backend.exe")) {
  throw "Backend build failed: dist\sai-backend.exe was not created."
}

Write-Host "Building static frontend..."
Remove-Item -Recurse -Force .\out -ErrorAction SilentlyContinue
$env:NEXT_PUBLIC_BACKEND_URL = "http://127.0.0.1:8000"
npm run build

if (!(Test-Path ".\out\chat.html")) {
  throw "Frontend build failed: out\chat.html was not created."
}

Write-Host "Cleaning old release folder..."
cmd /c rmdir /s /q release 2>$null

if (Test-Path ".\release") {
  throw "release folder is still locked. Restart your laptop, then run build-windows.ps1 again before opening S.A.I."
}

Write-Host "Building Electron unpacked app..."
npx electron-builder --win --x64 --dir

if (!(Test-Path ".\release\win-unpacked\S.A.I.exe")) {
  throw "Electron build failed: release\win-unpacked\S.A.I.exe was not created."
}

Write-Host ""
Write-Host "Build complete."
Write-Host "Run:"
Write-Host ".\release\win-unpacked\S.A.I.exe"