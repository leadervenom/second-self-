$ErrorActionPreference = "Stop"
Write-Host "Testing health..."
Invoke-RestMethod http://127.0.0.1:8000/health

Write-Host "Testing demo onboarding..."
$body = @{ name="Vajhra"; email=""; context="student building a Windows AI assistant"; session_id="demo-local" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/onboard -ContentType "application/json" -Body $body
