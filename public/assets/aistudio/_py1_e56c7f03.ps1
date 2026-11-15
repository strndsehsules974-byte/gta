$py = 'c:\Users\admin\dilkush007\.venv\Scripts\python.exe'
Set-Location 'c:\Users\admin\dilkush007'
& $py '_e2e_probe.py' 2>&1 | ForEach-Object { Write-Host "PROBE: $_" }
Write-Host "PROBE_EXIT=$LASTEXITCODE"
& $py '_authcheck.py' 2>&1 | ForEach-Object { Write-Host "AUTH: $_" }
Write-Host "AUTH_EXIT=$LASTEXITCODE"
