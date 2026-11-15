$py = 'c:\Users\admin\dilkush007\.venv\Scripts\python.exe'
Set-Location 'c:\Users\admin\dilkush007'
& $py '_e2e_probe2.py' 2>&1 | ForEach-Object { Write-Host "PROBE2: $_" }
Write-Host "PROBE2_EXIT=$LASTEXITCODE"
& $py '_authcheck.py' 2>&1 | ForEach-Object { Write-Host "AUTH: $_" }
Write-Host "AUTH_EXIT=$LASTEXITCODE"
