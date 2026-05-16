$ErrorActionPreference = "Stop"

if (!(Test-Path ".venv\Scripts\python.exe")) {
  throw "Virtual environment missing. Run .\setup-windows.ps1 first."
}

$env:DEMO_MODE = if ($env:DEMO_MODE) { $env:DEMO_MODE } else { "true" }
$env:HOST = "127.0.0.1"
$env:PORT = "8000"
$env:ALLOWED_ORIGINS = "http://localhost:3000"

& .\.venv\Scripts\python.exe -m uvicorn src.server:app --host 127.0.0.1 --port 8000 --reload
