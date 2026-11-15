$py = 'c:\Users\admin\dilkush007\.venv\Scripts\python.exe'
Set-Location 'c:\Users\admin\dilkush007'
& $py '_authcheck.py' 2>&1 | ForEach-Object { Write-Host "AUTH: $_" }
Write-Host "AUTH_EXIT=$LASTEXITCODE"
Write-Host '--- RESULT ---'
Get-Content '_authcheck.txt' -Encoding UTF8 | ForEach-Object { Write-Host $_ }
Write-Host 'AUTHDONE'
